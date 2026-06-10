# Computer Vision Skills — Comprehensive Guide

## 1. OpenCV Fundamentals

### Installation & Basics

```python
import cv2
import numpy as np
import matplotlib.pyplot as plt

# Read image
img = cv2.imread('image.jpg')  # BGR format
print(f"Shape: {img.shape}")   # (H, W, C)
print(f"Data type: {img.dtype}")

# Display
cv2.imshow('Window', img)
cv2.waitKey(0)          # Wait for key press
cv2.destroyAllWindows()

# Convert color spaces
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)

# Accessing/modifying pixels
pixel = img[100, 200]  # BGR value
img[100:200, 200:300] = [0, 255, 0]  # Green rectangle

# ROI extraction
roi = img[100:300, 200:400]
img[0:200, 0:200] = roi  # Copy region

# Splitting/merging channels
b, g, r = cv2.split(img)
merged = cv2.merge([b, g, r])

# Image arithmetic
brightened = cv2.add(img, 50)  # Saturating addition
blended = cv2.addWeighted(img1, 0.7, img2, 0.3, 0)

# Bitwise operations
mask = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)[1]
anded = cv2.bitwise_and(img, img, mask=mask)
ored = cv2.bitwise_or(img, img, mask=mask)
xored = cv2.bitwise_xor(img, img, mask=mask)
notted = cv2.bitwise_not(img)
```

### Drawing

```python
# Create blank image
canvas = np.zeros((500, 500, 3), dtype=np.uint8)

# Lines
cv2.line(canvas, (10, 10), (490, 490), (0, 255, 0), thickness=2)

# Rectangle
cv2.rectangle(canvas, (50, 50), (200, 200), (255, 0, 0), thickness=2)
cv2.rectangle(canvas, (250, 50), (400, 200), (0, 0, 255), thickness=-1)  # Filled

# Circle
cv2.circle(canvas, (250, 350), 100, (0, 255, 0), thickness=3)
cv2.circle(canvas, (250, 350), 50, (255, 0, 0), thickness=-1)

# Ellipse
cv2.ellipse(canvas, (250, 250), (100, 50), 45, 0, 360, (255, 255, 0), 2)

# Polygon
pts = np.array([[100, 50], [200, 50], [150, 150]], np.int32)
cv2.polylines(canvas, [pts], isClosed=True, color=(0, 255, 255), thickness=2)

# Text
font = cv2.FONT_HERSHEY_SIMPLEX
cv2.putText(canvas, 'OpenCV', (150, 400), font, 2, (255, 255, 255), 2, cv2.LINE_AA)
```

## 2. Image Filtering & Processing

### Kernels & Convolution

```python
import cv2
import numpy as np

image = cv2.imread('image.jpg', 0)

# Custom kernel convolution
kernel = np.array([[-1, -1, -1],
                   [-1,  8, -1],
                   [-1, -1, -1]])  # Edge detection kernel
filtered = cv2.filter2D(image, -1, kernel)

# Built-in filters
blur = cv2.blur(image, (5, 5))                          # Simple average
gaussian = cv2.GaussianBlur(image, (5, 5), sigmaX=1.5)  # Gaussian blur
median = cv2.medianBlur(image, 5)                       # Median (good for salt-pepper)
bilateral = cv2.bilateralFilter(image, 9, 75, 75)       # Edge-preserving
```

### Edge Detection

```python
# Sobel (gradient-based)
sobel_x = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
sobel_y = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
sobel_mag = np.sqrt(sobel_x**2 + sobel_y**2)
sobel_mag = np.uint8(np.clip(sobel_mag, 0, 255))

# Scharr (more accurate)
scharr_x = cv2.Scharr(image, cv2.CV_64F, 1, 0)
scharr_y = cv2.Scharr(image, cv2.CV_64F, 0, 1)

# Laplacian
laplacian = cv2.Laplacian(image, cv2.CV_64F)

# Canny Edge Detector (multi-stage)
edges = cv2.Canny(image, threshold1=50, threshold2=150, apertureSize=3)
# threshold1: low threshold for edge linking
# threshold2: high threshold for strong edge detection

# Adaptive Canny
def auto_canny(image, sigma=0.33):
    median = np.median(image)
    lower = int(max(0, (1.0 - sigma) * median))
    upper = int(min(255, (1.0 + sigma) * median))
    return cv2.Canny(image, lower, upper)

edges = auto_canny(image)
```

### Morphological Operations

```python
kernel = np.ones((5, 5), np.uint8)

erosion = cv2.erode(binary, kernel, iterations=1)       # Removes boundary pixels
dilation = cv2.dilate(binary, kernel, iterations=1)     # Adds boundary pixels
opening = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)   # Erosion -> Dilation (removes noise)
closing = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)  # Dilation -> Erosion (fills holes)
gradient = cv2.morphologyEx(binary, cv2.MORPH_GRADIENT, kernel)  # Difference between dilation and erosion
tophat = cv2.morphologyEx(binary, cv2.MORPH_TOPHAT, kernel)      # Original - opening
blackhat = cv2.morphologyEx(binary, cv2.MORPH_BLACKHAT, kernel)  # Closing - original

# Custom kernels
cross_kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (5, 5))
ellipse_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
```

### Thresholding

```python
# Simple thresholding
ret, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
ret, thresh_inv = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
ret, thresh_trunc = cv2.threshold(gray, 127, 255, cv2.THRESH_TRUNC)
ret, thresh_tozero = cv2.threshold(gray, 127, 255, cv2.THRESH_TOZERO)

# Adaptive thresholding
adaptive_mean = cv2.adaptiveThreshold(
    gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2
)
adaptive_gaussian = cv2.adaptiveThreshold(
    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
)

# Otsu's method (automatic threshold)
ret, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

# Triangle threshold
ret, triangle = cv2.threshold(gray, 0, 255, cv2.THRESH_TRIANGLE)
```

### Histograms

```python
# Grayscale histogram
hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
plt.plot(hist)
plt.title('Grayscale Histogram')
plt.show()

# Color histogram
colors = ('b', 'g', 'r')
for i, color in enumerate(colors):
    hist = cv2.calcHist([image], [i], None, [256], [0, 256])
    plt.plot(hist, color=color)
plt.show()

# Histogram equalization (improves contrast)
equalized = cv2.equalizeHist(gray)

# CLAHE (adaptive histogram equalization)
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
clahe_result = clahe.apply(gray)

# Histogram backprojection (object detection via color)
roi_hist = cv2.calcHist([hsv_roi], [0, 1], None, [180, 256], [0, 180, 0, 256])
cv2.normalize(roi_hist, roi_hist, 0, 255, cv2.NORM_MINMAX)
backproj = cv2.calcBackProject([hsv], [0, 1], roi_hist, [0, 180, 0, 256], 1)
```

## 3. Feature Detection & Matching

### Keypoint Detectors

```python
# Harris Corner Detection
gray = np.float32(gray)
harris = cv2.cornerHarris(gray, blockSize=2, ksize=3, k=0.04)
harris = cv2.dilate(harris, None)
image[harris > 0.01 * harris.max()] = [0, 0, 255]

# Shi-Tomasi (good features to track)
corners = cv2.goodFeaturesToTrack(gray, maxCorners=100, qualityLevel=0.01, minDistance=10)
corners = np.int0(corners)
for corner in corners:
    x, y = corner.ravel()
    cv2.circle(image, (x, y), 3, 255, -1)

# SIFT (Scale-Invariant Feature Transform)
sift = cv2.SIFT_create()
keypoints, descriptors = sift.detectAndCompute(gray, None)
image_sift = cv2.drawKeypoints(image, keypoints, None, flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

# SURF (Speeded-Up Robust Features) — faster than SIFT
# surf = cv2.xfeatures2d.SURF_create(400)
# keypoints, descriptors = surf.detectAndCompute(gray, None)

# ORB (Oriented FAST and Rotated BRIEF) — free, fast
orb = cv2.ORB_create(nfeatures=1000)
keypoints, descriptors = orb.detectAndCompute(gray, None)
image_orb = cv2.drawKeypoints(image, keypoints, None, color=(0, 255, 0))

# FAST (Features from Accelerated Segment Test)
fast = cv2.FastFeatureDetector_create(threshold=50)
keypoints = fast.detect(gray, None)

# BRIEF descriptor
brief = cv2.xfeatures2d.BriefDescriptorExtractor_create()
keypoints, descriptors = brief.compute(gray, keypoints)

# AKAZE (Accelerated KAZE)
akaze = cv2.AKAZE_create()
keypoints, descriptors = akaze.detectAndCompute(gray, None)

# BRISK (Binary Robust Invariant Scalable Keypoints)
brisk = cv2.BRISK_create()
keypoints, descriptors = brisk.detectAndCompute(gray, None)
```

### Feature Matching

```python
# Load images
img1 = cv2.imread('image1.jpg', 0)
img2 = cv2.imread('image2.jpg', 0)

# Detect keypoints and descriptors
sift = cv2.SIFT_create()
kp1, des1 = sift.detectAndCompute(img1, None)
kp2, des2 = sift.detectAndCompute(img2, None)

# Brute-Force Matcher
bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)
matches = bf.match(des1, des2)
matches = sorted(matches, key=lambda x: x.distance)

# Draw top 20 matches
matched_img = cv2.drawMatches(
    img1, kp1, img2, kp2, matches[:20], None,
    flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
)

# FLANN-based Matcher (faster for large datasets)
FLANN_INDEX_KDTREE = 1
index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
search_params = dict(checks=50)
flann = cv2.FlannBasedMatcher(index_params, search_params)
matches = flann.knnMatch(des1, des2, k=2)

# Lowe's ratio test
good_matches = []
for m, n in matches:
    if m.distance < 0.7 * n.distance:
        good_matches.append(m)

# Homography estimation
if len(good_matches) > 10:
    src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

    # Warp image
    h, w = img1.shape
    warped = cv2.warpPerspective(img1, H, (w * 2, h))
    warped[0:h, 0:w] = img2

# Feature matching with ORB
orb = cv2.ORB_create()
kp1, des1 = orb.detectAndCompute(img1, None)
kp2, des2 = orb.detectAndCompute(img2, None)

bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
matches = bf.match(des1, des2)
matches = sorted(matches, key=lambda x: x.distance)
```

## 4. Contour Analysis

```python
# Find contours
_, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
contours, hierarchy = cv2.findContours(
    binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
)
# RETR_EXTERNAL: only outermost contours
# RETR_TREE: all contours with hierarchy
# RETR_LIST: all contours without hierarchy

# Draw contours
display = np.zeros_like(image)
cv2.drawContours(display, contours, -1, (0, 255, 0), 2)  # All contours
cv2.drawContours(display, contours, 3, (0, 0, 255), 3)    # Specific contour

# Contour features
for i, cnt in enumerate(contours):
    area = cv2.contourArea(cnt)
    perimeter = cv2.arcLength(cnt, closed=True)

    if area < 100:  # Filter small noise
        continue

    # Bounding rectangle
    x, y, w, h = cv2.boundingRect(cnt)
    cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # Rotated rectangle
    rect = cv2.minAreaRect(cnt)
    box = cv2.boxPoints(rect)
    box = np.int0(box)
    cv2.drawContours(image, [box], 0, (0, 0, 255), 2)

    # Minimum enclosing circle
    (cx, cy), radius = cv2.minEnclosingCircle(cnt)
    center = (int(cx), int(cy))
    radius = int(radius)
    cv2.circle(image, center, radius, (255, 0, 0), 2)

    # Fit ellipse
    if len(cnt) >= 5:
        ellipse = cv2.fitEllipse(cnt)
        cv2.ellipse(image, ellipse, (255, 255, 0), 2)

    # Moments
    M = cv2.moments(cnt)
    if M['m00'] != 0:
        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])
        cv2.circle(image, (cx, cy), 5, (0, 0, 255), -1)

    # Contour approximation
    epsilon = 0.02 * cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, epsilon, True)
    cv2.drawContours(image, [approx], 0, (255, 0, 255), 2)

    # Convex hull
    hull = cv2.convexHull(cnt)
    cv2.drawContours(image, [hull], 0, (0, 255, 255), 2)

    # Shape classification
    vertices = len(approx)
    if vertices == 3:
        shape = "Triangle"
    elif vertices == 4:
        aspect_ratio = w / float(h)
        shape = "Square" if 0.95 <= aspect_ratio <= 1.05 else "Rectangle"
    elif vertices == 5:
        shape = "Pentagon"
    elif vertices > 10:
        shape = "Circle"
    else:
        shape = "Unknown"

    # Label
    cv2.putText(image, shape, (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
```

## 5. Object Detection

### YOLO (Ultralytics)

```python
from ultralytics import YOLO

# Load model
model = YOLO('yolov8n.pt')  # nano, small, medium, large, xlarge

# Single image inference
results = model('image.jpg')
results[0].show()           # Display with boxes
results[0].save('output.jpg')  # Save annotated image

# Batch inference
results = model(['img1.jpg', 'img2.jpg'], stream=True)

# Process results
for r in results:
    boxes = r.boxes.xyxy     # Bounding boxes in xyxy format
    confs = r.boxes.conf     # Confidence scores
    cls = r.boxes.cls        # Class IDs
    names = r.names           # Class names

    for box, conf, cls_id in zip(boxes, confs, cls):
        x1, y1, x2, y2 = map(int, box)
        label = f"{r.names[int(cls_id)]} {conf:.2f}"
        print(f"{label}: ({x1},{y1}) -> ({x2},{y2})")

# Video inference
results = model('video.mp4', save=True, save_txt=True)

# Webcam
results = model(0, show=True, stream=True)

# Custom training
results = model.train(
    data='dataset.yaml',
    epochs=100,
    imgsz=640,
    batch=16,
    device='cuda',
    lr0=0.01,
    augment=True,
    patience=20,
)

# Export to ONNX
model.export(format='onnx', imgsz=640, half=True)
```

### DETR (Transformers for Detection)

```python
from transformers import DetrImageProcessor, DetrForObjectDetection
import torch
from PIL import Image

# Load model
processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50")
model = DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50")

# Process image
image = Image.open("image.jpg")
inputs = processor(images=image, return_tensors="pt")

# Inference
with torch.no_grad():
    outputs = model(**inputs)

# Post-process
target_sizes = torch.tensor([image.size[::-1]])
results = processor.post_process_object_detection(
    outputs, target_sizes=target_sizes, threshold=0.5
)[0]

for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
    box = [round(i, 2) for i in box.tolist()]
    print(f"Detected {model.config.id2label[label.item()]} with confidence "
          f"{round(score.item(), 3)} at location {box}")

# Custom fine-tuning (DETR)
# from transformers import DetrForObjectDetection, DetrConfig
# config = DetrConfig.from_pretrained("facebook/detr-resnet-50", num_labels=num_classes)
# model = DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50", config=config)
```

## 6. Segmentation

### U-Net (Medical/Semantic)

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class UNet(nn.Module):
    def __init__(self, n_channels, n_classes):
        super(UNet, self).__init__()
        self.inc = DoubleConv(n_channels, 64)
        self.down1 = Down(64, 128)
        self.down2 = Down(128, 256)
        self.down3 = Down(256, 512)
        self.down4 = Down(512, 1024)
        self.up1 = Up(1024, 512)
        self.up2 = Up(512, 256)
        self.up3 = Up(256, 128)
        self.up4 = Up(128, 64)
        self.outc = OutConv(64, n_classes)

    def forward(self, x):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)
        x = self.up1(x5, x4)
        x = self.up2(x, x3)
        x = self.up3(x, x2)
        x = self.up4(x, x1)
        logits = self.outc(x)
        return logits

class DoubleConv(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.conv(x)

class Down(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.mpconv = nn.Sequential(
            nn.MaxPool2d(2),
            DoubleConv(in_ch, out_ch)
        )

    def forward(self, x):
        return self.mpconv(x)

class Up(nn.Module):
    def __init__(self, in_ch, out_ch, bilinear=True):
        super().__init__()
        if bilinear:
            self.up = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        else:
            self.up = nn.ConvTranspose2d(in_ch, in_ch // 2, 2, stride=2)
        self.conv = DoubleConv(in_ch, out_ch)

    def forward(self, x1, x2):
        x1 = self.up(x1)
        diffY = x2.size()[2] - x1.size()[2]
        diffX = x2.size()[3] - x1.size()[3]
        x1 = F.pad(x1, [diffX // 2, diffX - diffX // 2,
                        diffY // 2, diffY - diffY // 2])
        x = torch.cat([x2, x1], dim=1)
        return self.conv(x)

class OutConv(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.conv = nn.Conv2d(in_ch, out_ch, 1)

    def forward(self, x):
        return self.conv(x)
```

### Mask R-CNN (Instance Segmentation)

```python
import torchvision
from torchvision.models.detection import maskrcnn_resnet50_fpn

# Load pretrained
model = maskrcnn_resnet50_fpn(pretrained=True)
model.eval()

# Inference
image_tensor = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
with torch.no_grad():
    predictions = model([image_tensor])

# Process masks
masks = predictions[0]['masks'].numpy()  # (N, 1, H, W)
boxes = predictions[0]['boxes'].numpy()
labels = predictions[0]['labels'].numpy()
scores = predictions[0]['scores'].numpy()

# Visualize
import matplotlib.pyplot as plt
fig, axes = plt.subplots(1, 2, figsize=(12, 6))
axes[0].imshow(image)
axes[1].imshow(masks[0, 0], cmap='jet')
plt.show()
```

### SAM (Segment Anything Model)

```python
from segment_anything import sam_model_registry, SamPredictor
import torch

# Load SAM
sam = sam_model_registry["vit_h"](checkpoint="sam_vit_h_4b8939.pth")
predictor = SamPredictor(sam)

# Set image
predictor.set_image(rgb_image)

# Automatic mask generation
from segment_anything import SamAutomaticMaskGenerator
mask_generator = SamAutomaticMaskGenerator(sam)
masks = mask_generator.generate(rgb_image)

# Point prompts
input_point = np.array([[500, 375]])
input_label = np.array([1])  # 1 = foreground, 0 = background
masks, scores, logits = predictor.predict(
    point_coords=input_point,
    point_labels=input_label,
    multimask_output=True,
)

# Box prompts
input_box = np.array([200, 200, 600, 600])
masks, scores, logits = predictor.predict(
    point_coords=None,
    point_labels=None,
    box=input_box[None, :],
    multimask_output=False,
)
```

## 7. Image Classification

### EfficientNet Classification

```python
import timm
import torch
from PIL import Image
from torchvision import transforms

# Load pretrained EfficientNet
model = timm.create_model('efficientnet_b0', pretrained=True)
model.eval()

# Preprocessing
transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# Inference
image = Image.open('image.jpg').convert('RGB')
input_tensor = transform(image).unsqueeze(0)

with torch.no_grad():
    output = model(input_tensor)

# ImageNet class mapping
probs = torch.nn.functional.softmax(output[0], dim=0)
top5_probs, top5_indices = torch.topk(probs, 5)

# Load ImageNet labels
import json
with open('imagenet_labels.json') as f:
    labels = json.load(f)

for i in range(5):
    print(f"{labels[top5_indices[i]]}: {top5_probs[i]:.3f}")
```

### ViT Classification

```python
from transformers import ViTForImageClassification, ViTImageProcessor

# Load processor and model
processor = ViTImageProcessor.from_pretrained('google/vit-base-patch16-224')
model = ViTForImageClassification.from_pretrained('google/vit-base-patch16-224')

# Process image
image = Image.open('image.jpg')
inputs = processor(images=image, return_tensors="pt")

# Inference
with torch.no_grad():
    outputs = model(**inputs)
    logits = outputs.logits
    predicted_class_idx = logits.argmax(-1).item()

print(f"Predicted class: {model.config.id2label[predicted_class_idx]}")
```

### CLIP (Zero-Shot Classification)

```python
import clip
import torch
from PIL import Image

# Load model
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# Prepare image
image = preprocess(Image.open("image.jpg")).unsqueeze(0).to(device)

# Candidate labels
candidate_labels = ["cat", "dog", "car", "tree", "person", "building"]
text = clip.tokenize(candidate_labels).to(device)

# Inference
with torch.no_grad():
    logits_per_image, logits_per_text = model(image, text)
    probs = logits_per_image.softmax(dim=-1).cpu().numpy()[0]

# Results
for label, prob in zip(candidate_labels, probs):
    print(f"{label}: {prob:.3f}")
```

## 8. OCR (Optical Character Recognition)

### Tesseract

```python
import pytesseract
from PIL import Image
import re

# Basic usage
text = pytesseract.image_to_string(Image.open('text_image.png'))
print(text)

# Configuration options
custom_config = r'--oem 3 --psm 6'
text = pytesseract.image_to_string(image, config=custom_config)

# OEM modes:
# 0: Legacy Tesseract only
# 1: LSTM only
# 2: Legacy + LSTM
# 3: Default (based on available)

# PSM modes:
# 3: Fully automatic page segmentation
# 4: Single column of text
# 6: Single uniform block of text
# 7: Single line of text
# 8: Single word
# 10: Single character
# 13: Raw line (treat as text line)

# Get bounding boxes
boxes = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
for i in range(len(boxes['text'])):
    if int(boxes['conf'][i]) > 60:  # Confidence threshold
        (x, y, w, h) = (boxes['left'][i], boxes['top'][i],
                        boxes['width'][i], boxes['height'][i])
        text = boxes['text'][i]
        image = cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
        image = cv2.putText(image, text, (x, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

# Get word-level results
results = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
text_blocks = []
for text in results['text']:
    if text.strip():
        text_blocks.append(text.strip())

# Language support
text_french = pytesseract.image_to_string(image, lang='fra')
text_japanese = pytesseract.image_to_string(image, lang='jpn')

# Custom whitelist (characters to recognize)
custom_config = r'-c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ --psm 6'
text = pytesseract.image_to_string(image, config=custom_config)
```

### PaddleOCR

```python
from paddleocr import PaddleOCR

# Initialize (downloads model on first run)
ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=True)

# Inference
result = ocr.ocr('image.jpg', cls=True)

# Parse results
for line in result[0]:
    bbox = line[0]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
    text = line[1][0]  # Recognized text
    confidence = line[1][1]  # Confidence score

    # Draw
    pts = np.array(bbox, np.int32)
    cv2.polylines(image, [pts], True, (0, 255, 0), 2)
    cv2.putText(image, f"{text} ({confidence:.2f})",
                tuple(pts[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

# Multi-language
ocr_multi = PaddleOCR(lang='ch')  # Chinese
ocr_japan = PaddleOCR(lang='japan')  # Japanese

# Export as structured text
texts = [line[1][0] for line in result[0]]
full_text = '\n'.join(texts)
```

### TrOCR (Transformer OCR)

```python
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image

# Load model
processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-printed")
model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed")

# Process image
image = Image.open("printed_text.png").convert("RGB")
pixel_values = processor(images=image, return_tensors="pt").pixel_values

# Generate
generated_ids = model.generate(pixel_values)
text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
print(text)

# Handwritten text
processor_hand = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
model_hand = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
```

## 9. Video Analysis

### Video Processing

```python
import cv2

# Read video
cap = cv2.VideoCapture('video.mp4')

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Process frame
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)

    cv2.imshow('Frame', edges)
    if cv2.waitKey(25) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# Write video
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('output.mp4', fourcc, 30.0, (640, 480))

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    processed = cv2.Canny(frame, 100, 200)
    processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
    out.write(processed)

out.release()

# Frame properties
fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration = total_frames / fps
```

### Object Tracking

```python
# OpenCV trackers
tracker_types = {
    'BOOSTING': cv2.legacy.TrackerBoosting_create,
    'MIL': cv2.legacy.TrackerMIL_create,
    'KCF': cv2.legacy.TrackerKCF_create,
    'TLD': cv2.legacy.TrackerTLD_create,
    'MEDIANFLOW': cv2.legacy.TrackerMedianFlow_create,
    'MOSSE': cv2.legacy.TrackerMOSSE_create,
    'CSRT': cv2.legacy.TrackerCSRT_create,
}

# Initialize tracker
cap = cv2.VideoCapture('video.mp4')
ret, frame = cap.read()
bbox = cv2.selectROI('Tracker', frame, False)
tracker = tracker_types['CSRT']()
tracker.init(frame, bbox)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    success, bbox = tracker.update(frame)
    if success:
        x, y, w, h = [int(v) for v in bbox]
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    else:
        cv2.putText(frame, "Lost", (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    cv2.imshow('Tracking', frame)
    if cv2.waitKey(30) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

### Optical Flow

```python
# Lucas-Kanade Optical Flow
cap = cv2.VideoCapture('video.mp4')

# Parameters for corner detection
feature_params = dict(maxCorners=100, qualityLevel=0.3, minDistance=7, blockSize=7)

# Parameters for Lucas-Kanade
lk_params = dict(winSize=(15, 15), maxLevel=2,
                 criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

ret, old_frame = cap.read()
old_gray = cv2.cvtColor(old_frame, cv2.COLOR_BGR2GRAY)
p0 = cv2.goodFeaturesToTrack(old_gray, mask=None, **feature_params)

mask = np.zeros_like(old_frame)
color = np.random.randint(0, 255, (100, 3))

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Calculate optical flow
    p1, st, err = cv2.calcOpticalFlowPyrLK(old_gray, frame_gray, p0, None, **lk_params)

    if p1 is not None:
        good_new = p1[st == 1]
        good_old = p0[st == 1]

        for i, (new, old) in enumerate(zip(good_new, good_old)):
            a, b = new.ravel()
            c, d = old.ravel()
            mask = cv2.line(mask, (int(a), int(b)), (int(c), int(d)), color[i].tolist(), 2)
            frame = cv2.circle(frame, (int(a), int(b)), 5, color[i].tolist(), -1)

    img = cv2.add(frame, mask)
    cv2.imshow('Optical Flow', img)

    old_gray = frame_gray.copy()
    p0 = good_new.reshape(-1, 1, 2)

    if cv2.waitKey(30) & 0xFF == ord('q'):
        break

# Dense Optical Flow (Farneback)
ret, frame1 = cap.read()
prvs = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
hsv = np.zeros_like(frame1)
hsv[..., 1] = 255

while True:
    ret, frame2 = cap.read()
    if not ret:
        break
    next_frame = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

    flow = cv2.calcOpticalFlowFarneback(prvs, next_frame, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    hsv[..., 0] = ang * 180 / np.pi / 2
    hsv[..., 2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    cv2.imshow('Dense Optical Flow', bgr)

    prvs = next_frame
    if cv2.waitKey(30) & 0xFF == ord('q'):
        break
```

### Action Recognition

```python
# 3D CNN for action recognition
import torch
import torch.nn as nn

class Action3DCNN(nn.Module):
    def __init__(self, num_classes=101):
        super().__init__()
        self.conv1 = nn.Conv3d(3, 64, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm3d(64)
        self.pool1 = nn.MaxPool3d(2)

        self.conv2 = nn.Conv3d(64, 128, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm3d(128)
        self.pool2 = nn.MaxPool3d(2)

        self.conv3 = nn.Conv3d(128, 256, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm3d(256)
        self.pool3 = nn.MaxPool3d(2)

        self.conv4 = nn.Conv3d(256, 256, kernel_size=3, padding=1)
        self.bn4 = nn.BatchNorm3d(256)
        self.pool4 = nn.AdaptiveAvgPool3d(1)

        self.fc = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(256, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes),
        )

    def forward(self, x):
        # x: (batch, channels, frames, height, width)
        x = self.pool1(F.relu(self.bn1(self.conv1(x))))
        x = self.pool2(F.relu(self.bn2(self.conv2(x))))
        x = self.pool3(F.relu(self.bn3(self.conv3(x))))
        x = self.pool4(F.relu(self.bn4(self.conv4(x))))
        x = x.view(x.size(0), -1)
        return self.fc(x)

# Use pretrained video model
# from torchvision.models.video import r3d_18, mc3_18, r2plus1d_18
# model = r3d_18(pretrained=True)
# model.fc = nn.Linear(512, num_classes)
```

## 10. Face Recognition

### Face Detection

```python
# Haar Cascade Classifier
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
faces = face_cascade.detectMultiScale(
    gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
)

for (x, y, w, h) in faces:
    cv2.rectangle(image, (x, y), (x + w, y + h), (255, 0, 0), 2)
    roi_gray = gray[y:y+h, x:x+w]
    roi_color = image[y:y+h, x:x+w]

    eyes = eye_cascade.detectMultiScale(roi_gray)
    for (ex, ey, ew, eh) in eyes:
        cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)

# DNN-based detection
net = cv2.dnn.readNetFromCaffe('deploy.prototxt', 'res10_300x300_ssd_iter_140000.caffemodel')
blob = cv2.dnn.blobFromImage(image, 1.0, (300, 300), (104.0, 177.0, 123.0))
net.setInput(blob)
detections = net.forward()

for i in range(detections.shape[2]):
    confidence = detections[0, 0, i, 2]
    if confidence > 0.5:
        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
        (x, y, x2, y2) = box.astype("int")
        cv2.rectangle(image, (x, y), (x2, y2), (0, 255, 0), 2)
```

### DeepFace

```python
from deepface import DeepFace

# Face verification
result = DeepFace.verify(img1_path="person1.jpg", img2_path="person2.jpg")
print(f"Verified: {result['verified']}")
print(f"Distance: {result['distance']}")

# Face recognition (find identity in database)
result = DeepFace.find(img_path="face.jpg", db_path="faces_db/")
# Returns DataFrame with matched identities

# Face analysis
analysis = DeepFace.analyze(img_path="face.jpg", actions=['age', 'gender', 'emotion', 'race'])
print(f"Age: {analysis[0]['age']}")
print(f"Gender: {analysis[0]['dominant_gender']}")
print(f"Emotion: {analysis[0]['dominant_emotion']}")

# Face embedding
embedding = DeepFace.represent(img_path="face.jpg", model_name="Facenet")
print(f"Embedding shape: {len(embedding[0]['embedding'])}")
```

### FaceNet & ArcFace

```python
# Using facenet-pytorch
from facenet_pytorch import MTCNN, InceptionResnetV1
import torch
from PIL import Image

# Face detection
mtcnn = MTCNN(image_size=160, margin=20, post_process=True)

# Face embedding model
resnet = InceptionResnetV1(pretrained='vggface2').eval()

# Process
img = Image.open('face.jpg')
face = mtcnn(img)  # Returns cropped face tensor (1, 3, 160, 160) or None

if face is not None:
    embedding = resnet(face.unsqueeze(0))
    print(f"Embedding: {embedding.shape}")

# Face recognition pipeline
def get_face_embedding(image_path):
    img = Image.open(image_path)
    face = mtcnn(img)
    if face is None:
        return None
    embedding = resnet(face.unsqueeze(0))
    return embedding.detach().numpy()

def compare_faces(emb1, emb2, threshold=0.8):
    dist = torch.nn.functional.pairwise_distance(
        torch.tensor(emb1), torch.tensor(emb2)
    ).item()
    return dist < threshold, dist
```

## 11. Image Generation

### Stable Diffusion (Diffusers)

```python
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
import torch

# Load pipeline
pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16,
    safety_checker=None,
)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
pipe = pipe.to("cuda")

# Text-to-image
prompt = "a beautiful mountain landscape, sunset, photorealistic, 8k"
negative_prompt = "blurry, low quality, distorted"

image = pipe(
    prompt=prompt,
    negative_prompt=negative_prompt,
    num_inference_steps=25,
    guidance_scale=7.5,
    width=512,
    height=512,
    generator=torch.Generator("cuda").manual_seed(42),
).images[0]

image.save("generated.png")

# Image-to-image (img2img)
from diffusers import StableDiffusionImg2ImgPipeline

pipe_i2i = StableDiffusionImg2ImgPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16,
)
pipe_i2i = pipe_i2i.to("cuda")

init_image = Image.open("sketch.png").convert("RGB").resize((512, 512))
result = pipe_i2i(
    prompt="detailed beautiful illustration",
    image=init_image,
    strength=0.75,  # How much to transform (0-1)
    num_inference_steps=50,
).images[0]
```

### ControlNet (Conditional Generation)

```python
from diffusers import StableDiffusionControlNetPipeline, ControlNetModel, UniPCMultistepScheduler
from diffusers.utils import load_image
import cv2
import numpy as np

# Load ControlNet
controlnet = ControlNetModel.from_pretrained(
    "lllyasviel/sd-controlnet-canny", torch_dtype=torch.float16
)

pipe = StableDiffusionControlNetPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    controlnet=controlnet,
    torch_dtype=torch.float16,
)
pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
pipe = pipe.to("cuda")

# Prepare conditioning image
image = load_image("input_image.jpg")
image = np.array(image)
image = cv2.Canny(image, 100, 200)
image = image[:, :, None]
image = np.concatenate([image, image, image], axis=2)
control_image = Image.fromarray(image)

# Generate
result = pipe(
    "detailed building, high quality, realistic",
    image=control_image,
    num_inference_steps=20,
    controlnet_conditioning_scale=1.0,
).images[0]
```

### ComfyUI Workflow Programmatic

```python
# ComfyUI workflows are JSON-based graphs
# Example minimal workflow via API
import json
import requests

def queue_prompt(prompt_workflow, server_address="127.0.0.1:8188"):
    p = {"prompt": prompt_workflow}
    data = json.dumps(p).encode('utf-8')
    requests.post(f"http://{server_address}/prompt", data=data)

# Workflow structure:
# {
#   "3": {
#     "class_type": "KSampler",
#     "inputs": {
#       "seed": 42,
#       "steps": 20,
#       "cfg": 7.5,
#       "sampler_name": "euler",
#       "scheduler": "normal",
#       "denoise": 1,
#       "model": ["4", 0],
#       "positive": ["6", 0],
#       "negative": ["7", 0],
#       "latent_image": ["5", 0]
#     }
#   },
#   "4": { "class_type": "CheckpointLoaderSimple", "inputs": { "ckpt_name": "sd_xl_base.safetensors" } },
#   "5": { "class_type": "EmptyLatentImage", "inputs": { "width": 1024, "height": 1024, "batch_size": 1 } },
#   "6": { "class_type": "CLIPTextEncode", "inputs": { "text": "prompt", "clip": ["4", 1] } },
#   "7": { "class_type": "CLIPTextEncode", "inputs": { "text": "negative", "clip": ["4", 1] } },
#   "8": { "class_type": "VAEDecode", "inputs": { "samples": ["3", 0], "vae": ["4", 2] } },
#   "9": { "class_type": "SaveImage", "inputs": { "filename_prefix": "output", "images": ["8", 0] } }
# }
```
