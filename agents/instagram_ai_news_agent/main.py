"""
Instagram AI News Agent
Scrolls Instagram feed, reads relevant posts deeply, generates PDF report, and emails summary.
"""
import os
import json
import asyncio
import logging
import re
import argparse
import shutil
import subprocess
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
import sys

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.browser_tools import BrowserTools
from tools.email_tools import EmailTools
from tools.pdf_tools import PDFReportGenerator
from tools.command_router import CommandRouter
from tools.instruction_loader import compose_system_prompt
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

try:
    import speech_recognition as sr
except Exception:
    sr = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - Instagram Agent - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# AI-related keywords to filter posts
AI_KEYWORDS = [
    'ai', 'artificial intelligence', 'machine learning', 'openai', 'gpt', 
    'claude', 'anthropic', 'meta ai', 'kimi', 'qwen', 'groq', 'ollama',
    'deep learning', 'neural network', 'llm', 'transformer', 'chatgpt',
    'gemini', 'mistral', 'codestral', 'together ai', 'replicate',
    'hugging face', 'diffusion', 'stable diffusion', 'midjourney',
    'generative ai', 'prompt', 'algorithm', 'data science', 'nlp',
    'computer vision', 'vision language model', 'multimodal'
]

WORLD_NEWS_KEYWORDS = [
    'breaking', 'war', 'conflict', 'election', 'policy', 'government',
    'earthquake', 'flood', 'hurricane', 'wildfire', 'global market',
    'stock market', 'geopolitical', 'summit', 'launch', 'new release',
    'major update', 'security breach', 'cyber attack', 'space mission'
]


def _keyword_present(text: str, keyword: str) -> bool:
    if not text or not keyword:
        return False

    if len(keyword) <= 3 and " " not in keyword:
        pattern = rf"\b{re.escape(keyword)}\b"
        return re.search(pattern, text) is not None

    return keyword in text


class InstagramAINNewsAgent:
    """
    Automates Instagram feed analysis for AI-related news and content.
    """
    
    def __init__(self, chrome_profile: Optional[str] = None):
        """
        Initialize the Instagram AI News Agent.
        
        Args:
            chrome_profile: Optional Chrome profile name to use for login
        """
        load_dotenv()
        self.chrome_profile = chrome_profile or os.getenv('INSTAGRAM_CHROME_PROFILE', 'Default')
        self.browser_tools = None
        self.email_tools = EmailTools()
        self.pdf_generator = PDFReportGenerator()
        self.command_router = CommandRouter()
        self.instagram_url = "https://www.instagram.com"
        self.posts_per_run = int(os.getenv('INSTAGRAM_POSTS_PER_RUN', '50'))
        self.scroll_pause_time = float(os.getenv('INSTAGRAM_SCROLL_PAUSE_TIME', '2.0'))
        self.max_scroll_attempts = int(os.getenv('INSTAGRAM_MAX_SCROLL_ATTEMPTS', '100'))
        self.check_interval_seconds = int(os.getenv('INSTAGRAM_CHECK_INTERVAL_SECONDS', '10800'))
        self.max_carousel_pages = int(os.getenv('INSTAGRAM_MAX_CAROUSEL_PAGES', '8'))
        self.video_audio_enabled = os.getenv('INSTAGRAM_VIDEO_AUDIO_CAPTURE_ENABLED', 'true').lower() == 'true'
        self.video_audio_seconds = int(os.getenv('INSTAGRAM_VIDEO_AUDIO_SAMPLE_SECONDS', '40'))
        self.auto_send_report_email = os.getenv('INSTAGRAM_AUTO_SEND_REPORT_EMAIL', 'true').lower() == 'true'

        root_dir = Path(__file__).parent.parent.parent
        self.state_file = root_dir / "tom_logs" / "instagram_agent_state.json"
        self.pid_file = root_dir / "tom_logs" / "instagram_agent.pid"
        self.history_file = root_dir / "tom_logs" / "instagram_agent_history.jsonl"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        self.posts = []
        self.ai_posts = []

        self.model_name = os.getenv('OLLAMA_MODEL', 'llama3.2:latest')
        self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.llm = None
        try:
            self.llm = ChatOllama(model=self.model_name, base_url=self.base_url, temperature=0.2)
        except Exception:
            self.llm = None

    def _now(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def _write_state(self, payload: Dict) -> None:
        data = dict(payload)
        data.setdefault("agent_name", "instagram_ai_news_agent")
        data.setdefault("updated_at", self._now())
        tmp = self.state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.state_file)

    def _append_history(self, payload: Dict) -> None:
        try:
            with self.history_file.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload) + "\n")
        except Exception:
            pass

    def _store_result(self, result: Dict) -> None:
        recent_runs = []
        try:
            if self.state_file.exists():
                state = json.loads(self.state_file.read_text(encoding="utf-8"))
                recent_runs = list(state.get("recent_runs", []))
        except Exception:
            recent_runs = []

        compact = {
            "timestamp": result.get("timestamp"),
            "success": result.get("success", False),
            "posts_extracted": result.get("posts_extracted", 0),
            "ai_posts_found": result.get("ai_posts_found", 0),
            "report_generated": result.get("report_generated", False),
            "email_sent": result.get("email_sent", False),
            "errors": result.get("errors", []),
        }
        recent_runs.insert(0, compact)
        recent_runs = recent_runs[:20]

        state_payload = {
            "status": "success" if result.get("success") else "incomplete",
            "running": self.pid_file.exists(),
            "last_run_at": result.get("timestamp"),
            "next_run_at": self._now(),
            "posts_extracted": result.get("posts_extracted", 0),
            "ai_posts_found": result.get("ai_posts_found", 0),
            "report_generated": result.get("report_generated", False),
            "email_sent": result.get("email_sent", False),
            "report_path": result.get("report_path"),
            "errors": result.get("errors", []),
            "recent_runs": recent_runs,
        }
        self._write_state(state_payload)
        self._append_history(compact)

    def write_pid_file(self) -> None:
        self.pid_file.write_text(str(os.getpid()), encoding="utf-8")

    def remove_pid_file(self) -> None:
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except Exception:
            pass
        
    async def init_browser(self):
        """Initialize and launch browser with Instagram profile."""
        logger.info(f"Initializing browser with Chrome profile: {self.chrome_profile}")
        self.browser_tools = BrowserTools()
        init_result = await self.browser_tools.init_browser(profile=self.chrome_profile)
        if init_result.get("status") != "success":
            raise RuntimeError(init_result.get("message", "Browser init failed"))
        logger.info("Browser initialized successfully")
        
    async def close_browser(self):
        """Close the browser and cleanup resources."""
        if self.browser_tools:
            await self.browser_tools.close_browser()
            logger.info("Browser closed")
    
    async def open_instagram(self) -> bool:
        """
        Open Instagram in the browser.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Opening Instagram: {self.instagram_url}")
            open_result = await self.browser_tools.open_url(self.instagram_url)
            if open_result.get("status") != "success":
                logger.error(f"Open URL failed: {open_result.get('message', 'unknown')}" )
                return False
            await asyncio.sleep(3)  # Wait for page load
            current_url = await self.browser_tools.get_current_url()
            if "instagram.com" not in (current_url or ""):
                logger.error(f"Instagram did not load correctly (current_url={current_url})")
                return False
            logger.info("Instagram opened successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to open Instagram: {e}")
            return False

    async def _extract_visible_feed_cards(self) -> List[Dict[str, Any]]:
        script = """
(() => {
  const cards = [];
  const articles = Array.from(document.querySelectorAll('article'));
  for (const article of articles) {
    const link = article.querySelector("a[href*='/p/'], a[href*='/reel/']");
    const authorNode = article.querySelector("header a, h2 a, h3 a");
    const textNode = article.querySelector("h1, h2, span, div[role='button'] span");
    const text = (textNode && textNode.innerText ? textNode.innerText : article.innerText || '').slice(0, 1200);
    const hasVideo = !!article.querySelector('video');
    const hasCarousel = !!article.querySelector("button[aria-label='Next'], button[aria-label='Next photo'], svg[aria-label='Carousel']");
    cards.push({
      url: link ? link.href : '',
      author: authorNode ? (authorNode.innerText || '') : '',
      text,
      has_video: hasVideo,
      has_carousel: hasCarousel,
    });
  }
  return cards;
})()
"""
        try:
            data = await self.browser_tools.execute_script(script)
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
            return []
        except Exception:
            return []

    def _score_relevance(self, text: str) -> int:
        normalized = (text or "").lower()
        ai_matches = sum(1 for kw in AI_KEYWORDS if _keyword_present(normalized, kw))
        world_matches = sum(1 for kw in WORLD_NEWS_KEYWORDS if _keyword_present(normalized, kw))
        news_bonus = 1 if any(token in normalized for token in ("news", "breaking", "update", "released")) else 0
        return (ai_matches * 2) + world_matches + news_bonus

    async def _open_post(self, post_url: str) -> bool:
        if not post_url:
            return False
        result = await self.browser_tools.open_url(post_url)
        if result.get("status") != "success":
            return False
        await asyncio.sleep(2)
        return True

    async def _extract_post_caption_text(self) -> str:
        script = """
(() => {
  const nodes = Array.from(document.querySelectorAll("article h1, article span, article div[role='button'] span"));
  const merged = nodes.map(n => (n && n.innerText ? n.innerText.trim() : '')).filter(Boolean).join(' ');
  return merged.slice(0, 5000);
})()
"""
        try:
            value = await self.browser_tools.execute_script(script)
            return value if isinstance(value, str) else ""
        except Exception:
            return ""

    async def _has_next_carousel_page(self) -> bool:
        script = """
(() => {
  const next = document.querySelector("button[aria-label='Next'], button[aria-label='Next photo'], button[aria-label='Next slide']");
  if (!next) return false;
  next.click();
  return true;
})()
"""
        try:
            return bool(await self.browser_tools.execute_script(script))
        except Exception:
            return False

    async def _extract_video_audio_context(self) -> str:
        dom_audio_text = ""
        script = """
(() => {
  const candidates = Array.from(document.querySelectorAll("video, track, [aria-label*='caption'], [aria-label*='audio'], [data-testid*='caption']"));
  const texts = candidates.map(n => (n.getAttribute && (n.getAttribute('aria-label') || n.getAttribute('alt'))) || n.innerText || '').filter(Boolean);
  const video = document.querySelector('video');
  const mediaSrc = video ? (video.currentSrc || video.src || '') : '';
  return { text: texts.join(' ').slice(0, 3000), media_src: mediaSrc };
})()
"""
        media_src = ""
        try:
            payload = await self.browser_tools.execute_script(script)
            if isinstance(payload, dict):
                dom_audio_text = str(payload.get("text", ""))
                media_src = str(payload.get("media_src", ""))
        except Exception:
            pass

        transcription = ""
        if self.video_audio_enabled and media_src.startswith("http"):
            transcription = await asyncio.to_thread(self._transcribe_media_url, media_src)

        parts = [part.strip() for part in [dom_audio_text, transcription] if part and part.strip()]
        return "\n".join(parts)

    def _transcribe_media_url(self, media_url: str) -> str:
        if not sr or not shutil.which("ffmpeg"):
            return ""

        temp_dir = Path(tempfile.mkdtemp(prefix="tom_ig_audio_"))
        media_file = temp_dir / "clip.mp4"
        wav_file = temp_dir / "clip.wav"

        try:
            urllib.request.urlretrieve(media_url, str(media_file))
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", str(media_file),
                    "-t", str(self.video_audio_seconds),
                    "-ac", "1",
                    "-ar", "16000",
                    str(wav_file),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            recognizer = sr.Recognizer()
            with sr.AudioFile(str(wav_file)) as source:
                audio_data = recognizer.record(source)
            try:
                return recognizer.recognize_google(audio_data)
            except Exception:
                return ""
        except Exception:
            return ""
        finally:
            try:
                for path in [media_file, wav_file]:
                    if path.exists():
                        path.unlink()
                temp_dir.rmdir()
            except Exception:
                pass

    async def _extract_post_pages(self, seed: Dict[str, Any]) -> Dict[str, Any]:
        page_notes = []
        seen_page_signatures = set()
        combined_audio = []
        page_index = 0
        has_video = bool(seed.get("has_video"))

        while page_index < self.max_carousel_pages:
            page_index += 1
            visible_text = await self.browser_tools.get_page_content()
            caption_text = await self._extract_post_caption_text()
            audio_context = ""
            if has_video:
                audio_context = await self._extract_video_audio_context()
                if audio_context:
                    combined_audio.append(audio_context)

            combined_text = " ".join(part for part in [caption_text, visible_text] if part).strip()
            signature = (combined_text[:400] + (audio_context[:200] if audio_context else "")).strip().lower()
            if signature and signature not in seen_page_signatures:
                seen_page_signatures.add(signature)
                page_notes.append({
                    "page": page_index,
                    "text": combined_text[:4000],
                    "audio_context": audio_context[:2000],
                })

            moved = await self._has_next_carousel_page() if seed.get("has_carousel") else False
            if not moved:
                break
            await asyncio.sleep(1.1)

        merged_text = "\n\n".join(f"Page {item['page']}: {item['text']}" for item in page_notes)
        merged_audio = "\n".join(combined_audio)
        return {
            "pages": page_notes,
            "all_text": merged_text,
            "audio_text": merged_audio,
            "page_count": len(page_notes),
            "has_video": has_video,
        }

    async def _summarize_post(self, post_payload: Dict[str, Any]) -> str:
        text_blob = post_payload.get("all_text", "")
        audio_blob = post_payload.get("audio_text", "")
        combined = f"Visual and caption context:\n{text_blob}\n\nAudio or spoken context:\n{audio_blob}"

        if not self.llm:
            snippet = combined[:700]
            return snippet + ("..." if len(combined) > 700 else "")

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    compose_system_prompt(
                        (
                            "You summarize Instagram posts for a news brief. Keep it factual, concise, and useful. "
                            "Highlight key claims, named entities, and why this matters globally. "
                            "If the content appears unreliable or promotional, mention uncertainty."
                        ),
                        "instagram_ai_news_agent",
                        include_ui=True,
                    )
                ),
                (
                    "user",
                    "Summarize this single post from all pages/slides and audio context in 4-6 lines:\n\n{content}"
                ),
            ]
        )

        try:
            response = await asyncio.wait_for(
                (prompt | self.llm).ainvoke({"content": combined[:12000]}),
                timeout=35,
            )
            return str(getattr(response, "content", "")).strip() or combined[:700]
        except Exception:
            return combined[:700] + ("..." if len(combined) > 700 else "")
    
    async def extract_post_content(self, post_url: str, seed: Dict[str, Any]) -> Dict:
        """
        Extract content from a single visible post on the feed.
        Captures: post text, links, author, timestamp, and visibility.
        
        Returns:
            Dict with post data or empty dict if extraction fails
        """
        try:
            if not await self._open_post(post_url):
                return {}

            post_pages = await self._extract_post_pages(seed)
            all_text = post_pages.get("all_text", "")
            audio_text = post_pages.get("audio_text", "")
            relevance_score = self._score_relevance(f"{seed.get('text', '')}\n{all_text}\n{audio_text}")

            if relevance_score <= 0:
                return {
                    "url": post_url,
                    "author": seed.get("author", ""),
                    "text": seed.get("text", ""),
                    "visual_text": all_text[:3000],
                    "audio_text": audio_text[:2000],
                    "is_relevant": False,
                    "relevance_score": 0,
                    "page_count": post_pages.get("page_count", 0),
                    "has_video": post_pages.get("has_video", False),
                    "extracted_at": datetime.now().isoformat(),
                }

            summary = await self._summarize_post(post_pages)

            return {
                "url": post_url,
                "author": seed.get("author", ""),
                "text": seed.get("text", "")[:500],
                "visual_text": all_text[:5000],
                "audio_text": audio_text[:2500],
                "summary": summary,
                "is_relevant": True,
                "relevance_score": relevance_score,
                "page_count": post_pages.get("page_count", 0),
                "has_video": post_pages.get("has_video", False),
                "extracted_at": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to extract post content: {e}")
            return {}
        finally:
            try:
                await self.browser_tools.execute_script("window.history.back();")
                await asyncio.sleep(1.5)
            except Exception:
                pass
    
    async def scroll_feed(self, num_posts: int = 50, scroll_pause_time: float = 2.0) -> List[Dict]:
        """
        Scroll through Instagram feed and extract post data.
        
        Args:
            num_posts: Number of posts to try to extract
            scroll_pause_time: Seconds to wait between scrolls for content loading
            
        Returns:
            List of extracted post dictionaries
        """
        logger.info(f"Starting feed scroll - target: {num_posts} posts")
        extracted_posts = []
        seen_urls = set()
        scroll_attempts = 0
        max_scrolls = min(self.max_scroll_attempts, num_posts * 4)
        
        try:
            while len(extracted_posts) < num_posts and scroll_attempts < max_scrolls:
                cards = await self._extract_visible_feed_cards()
                for card in cards:
                    if len(extracted_posts) >= num_posts:
                        break

                    post_url = str(card.get("url", "")).strip()
                    if not post_url or post_url in seen_urls:
                        continue
                    seen_urls.add(post_url)

                    quick_score = self._score_relevance(f"{card.get('text', '')} {card.get('author', '')}")
                    if quick_score <= 0:
                        continue

                    post_data = await self.extract_post_content(post_url, card)
                    if post_data and post_data.get("is_relevant"):
                        extracted_posts.append(post_data)
                        logger.info(
                            "Collected relevant post %s (score=%s, pages=%s)",
                            len(extracted_posts),
                            post_data.get("relevance_score", 0),
                            post_data.get("page_count", 1),
                        )

                scroll_attempts += 1
                try:
                    await self.browser_tools.execute_script(
                        "window.scrollBy(0, Math.max(window.innerHeight * 0.85, 620));"
                    )
                    await asyncio.sleep(scroll_pause_time)
                    logger.info(f"Scroll {scroll_attempts}: collected {len(extracted_posts)} relevant posts")
                except Exception as e:
                    logger.warning(f"Scroll script failed: {e}")
                    break

                if not cards and scroll_attempts >= min(20, max_scrolls):
                    logger.warning("No usable Instagram cards extracted after multiple scrolls")
                    break
            
            logger.info(f"Feed scroll complete: extracted {len(extracted_posts)} posts")
            self.posts = extracted_posts
            return extracted_posts
            
        except Exception as e:
            logger.error(f"Error during feed scroll: {e}")
            return extracted_posts
    
    def classify_post(self, post: Dict) -> Dict:
        """
        Classify a post for AI relevance and generate summary.
        Uses local heuristics (keyword matching) or LLM if available.
        
        Args:
            post: Post data dictionary
            
        Returns:
            Classified post with importance rating (1-5) and summary
        """
        text = "\n".join(
            [
                str(post.get('visual_text', '')),
                str(post.get('text', '')),
                str(post.get('audio_text', '')),
                str(post.get('summary', '')),
            ]
        ).lower()

        relevance_score = self._score_relevance(text)
        keyword_matches = sum(1 for kw in AI_KEYWORDS if _keyword_present(text, kw))

        if relevance_score >= 8:
            importance = 5
        elif relevance_score >= 6:
            importance = 4
        elif relevance_score >= 3:
            importance = 3
        elif relevance_score >= 1:
            importance = 2
        else:
            importance = 0

        summary = str(post.get('summary', '')).strip()
        if not summary:
            summary = post.get('text', '')[:200]
        if len(summary) > 500:
            summary = summary[:500] + "..."
        
        classified_post = post.copy()
        classified_post['importance'] = importance
        classified_post['summary'] = summary
        classified_post['is_ai_related'] = importance > 0
        classified_post['is_relevant'] = importance > 0
        classified_post['relevance_score'] = relevance_score
        classified_post['keyword_matches'] = keyword_matches
        
        return classified_post
    
    def filter_ai_posts(self, posts: List[Dict]) -> List[Dict]:
        """
        Filter posts for AI relevance and classify them.
        
        Args:
            posts: List of extracted posts
            
        Returns:
            List of AI-related posts sorted by importance (high to low)
        """
        logger.info(f"Filtering {len(posts)} posts for AI/tech/world relevance")
        
        classified = [self.classify_post(post) for post in posts]
        ai_posts = [p for p in classified if p.get('is_ai_related', False)]
        
        # Sort by importance descending
        ai_posts.sort(key=lambda x: x.get('importance', 0), reverse=True)
        
        logger.info(f"Found {len(ai_posts)} relevant posts")
        self.ai_posts = ai_posts
        return ai_posts
    
    async def generate_report(self, ai_posts: List[Dict]) -> str:
        """
        Generate PDF report from AI posts.
        
        Args:
            ai_posts: List of classified AI posts
            
        Returns:
            Path to generated PDF file
        """
        logger.info(f"Generating PDF report with {len(ai_posts)} posts")
        
        # Create reports directory if it doesn't exist
        reports_dir = Path(__file__).parent.parent.parent / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate report
        report_path = self.pdf_generator.generate(
            posts=ai_posts,
            output_dir=str(reports_dir),
            title="Instagram AI News Report",
            include_importance=True,
            include_links=True
        )
        
        logger.info(f"Report generated: {report_path}")
        return report_path
    
    async def send_report_email(self, pdf_path: str, recipient: Optional[str] = None) -> bool:
        """
        Email the generated PDF report.
        
        Args:
            pdf_path: Path to PDF file to send
            recipient: Email recipient (defaults to EMAIL_ADDRESS from env)
            
        Returns:
            bool: True if email was sent successfully
        """
        recipient = recipient or os.getenv('EMAIL_ADDRESS')
        
        if not recipient:
            logger.error("No recipient email configured")
            return False
        
        logger.info(f"Preparing to send report to {recipient}")
        
        try:
            subject = f"Instagram AI News Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            summary_lines = [
                f"{len(self.ai_posts)} AI or world-news items were preserved from the feed.",
                "Posts were filtered by relevance before reporting.",
                "Carousels were expanded and video context was sampled when available.",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ]
            highlights = []
            for post in self.ai_posts[:3]:
                highlights.append(
                    {
                        "importance": post.get("importance", 0),
                        "heading": post.get("author", "Instagram post") or "Instagram post",
                        "detail": post.get("summary", post.get("text", ""))[:260],
                        "source": post.get("url", ""),
                    }
                )

            report_bundle = self.email_tools.format_report_email(
                title="Instagram AI News Report",
                summary_lines=summary_lines,
                highlights=highlights,
            )
            body = report_bundle["plain_text"]
            
            # Always create a visible draft entry for traceability.
            await self.email_tools.draft_email(recipient, subject, body, attachments=[pdf_path])
            logger.info("Instagram report draft prepared")

            if self.auto_send_report_email:
                result = await self.email_tools.send_email_direct(recipient, subject, body, attachments=[pdf_path])
            else:
                result = await self.email_tools.send_email(recipient, subject, body, attachments=[pdf_path])

            if isinstance(result, dict) and result.get("status") == "success":
                logger.info(f"Email sent successfully to {recipient}")
                return True
            else:
                logger.warning("Email sending was cancelled by user")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def run_workflow(self) -> Dict:
        """
        Execute the complete Instagram AI news workflow:
        1. Open Instagram
        2. Scroll feed and extract posts
        3. Filter for AI-related content
        4. Generate PDF report
        5. Email report to user
        
        Returns:
            Dict with workflow result and status
        """
        result = {
            'success': False,
            'posts_extracted': 0,
            'ai_posts_found': 0,
            'report_generated': False,
            'email_sent': False,
            'report_path': None,
            'timestamp': datetime.now().isoformat(),
            'errors': []
        }
        
        try:
            # Initialize browser
            await self.init_browser()
            
            # Open Instagram
            if not await self.open_instagram():
                result['errors'].append("Failed to open Instagram")
                return result
            
            # Scroll feed and extract posts
            posts = await self.scroll_feed(num_posts=self.posts_per_run, scroll_pause_time=self.scroll_pause_time)
            result['posts_extracted'] = len(posts)
            
            if not posts:
                result['errors'].append("No posts extracted from feed")
                return result
            
            # Filter for AI posts
            ai_posts = self.filter_ai_posts(posts)
            result['ai_posts_found'] = len(ai_posts)
            
            if not ai_posts:
                logger.info("No AI-related posts found in current feed")
                result['errors'].append("No AI-related posts found")
                return result
            
            # Generate PDF report
            try:
                report_path = await self.generate_report(ai_posts)
                result['report_generated'] = True
                result['report_path'] = report_path
            except Exception as e:
                result['errors'].append(f"PDF generation failed: {e}")
                logger.error(f"PDF generation error: {e}")
                return result
            
            # Send email
            try:
                email_sent = await self.send_report_email(report_path)
                result['email_sent'] = email_sent
            except Exception as e:
                result['errors'].append(f"Email delivery failed: {e}")
                logger.error(f"Email error: {e}")
            
            result['success'] = result['report_generated'] and result['email_sent']
            
        except Exception as e:
            result['errors'].append(f"Workflow error: {e}")
            logger.error(f"Workflow execution error: {e}")
        finally:
            self._store_result(result)
            await self.close_browser()
        
        return result

    async def run_forever(self):
        self.write_pid_file()
        logger.info("Instagram daemon mode started")
        logger.info(f"Interval: {self.check_interval_seconds}s")
        try:
            while True:
                await self.run_workflow()
                await asyncio.sleep(self.check_interval_seconds)
        except asyncio.CancelledError:
            raise
        except KeyboardInterrupt:
            logger.info("Instagram daemon interrupted")
        finally:
            self.remove_pid_file()


async def main():
    """
    Main entry point for the Instagram AI News Agent.
    """
    parser = argparse.ArgumentParser(description="Instagram AI News Agent")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    parser.add_argument("--once", action="store_true", help="Run one workflow and exit")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Instagram AI News Agent - Starting Workflow")
    logger.info("=" * 60)

    agent = InstagramAINNewsAgent()
    if args.daemon:
        await agent.run_forever()
        return {
            "success": True,
            "message": "Instagram agent daemon started"
        }

    result = await agent.run_workflow()
    
    # Print summary
    logger.info("=" * 60)
    logger.info("WORKFLOW SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Status: {'SUCCESS' if result['success'] else 'INCOMPLETE'}")
    logger.info(f"Posts Extracted: {result['posts_extracted']}")
    logger.info(f"AI Posts Found: {result['ai_posts_found']}")
    logger.info(f"Report Generated: {result['report_generated']}")
    logger.info(f"Email Sent: {result['email_sent']}")
    
    if result['report_path']:
        logger.info(f"Report Location: {result['report_path']}")
    
    if result['errors']:
        logger.warning("Errors encountered:")
        for error in result['errors']:
            logger.warning(f"  - {error}")
    
    logger.info("=" * 60)
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
