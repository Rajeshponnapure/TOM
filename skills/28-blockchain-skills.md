# Blockchain Skills — Comprehensive Guide

## 1. Solidity Fundamentals

### Data Types

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract DataTypes {
    // Value types
    bool public isActive = true;
    int256 public signed = -42;      // Signed integer (-2^255 to 2^255-1)
    uint256 public unsigned = 42;    // Unsigned integer (0 to 2^256-1)
    uint8 public small = 255;        // 8-bit unsigned (0-255)
    address public owner = msg.sender; // 20-byte Ethereum address
    address payable public receiver;   // Can receive ETH
    bytes32 public hash = keccak256("data"); // 32-byte fixed-size byte array
    bytes1 public singleByte = 0x42;

    // Reference types
    string public name = "Alice";        // Dynamic UTF-8 string
    bytes public data = hex"deadbeef";   // Dynamic byte array
    uint256[] public numbers = [1, 2, 3]; // Dynamic array
    uint256[5] public fixed = [1,2,3,4,5]; // Fixed-size array

    // Enum
    enum Status { Pending, Active, Completed, Cancelled }
    Status public status = Status.Pending;

    // Struct
    struct User {
        string name;
        uint256 age;
        address wallet;
    }
    User public user = User("Bob", 25, msg.sender);

    // Mapping
    mapping(address => uint256) public balances;
    mapping(uint256 => mapping(address => bool)) public hasVoted; // Nested
    mapping(address => User) public users;

    // String operations
    function concat(string memory a, string memory b) public pure returns (string memory) {
        return string.concat(a, b);
    }
}
```

### Function Types & Visibility

```solidity
contract VisibilityDemo {
    // Visibility modifiers
    function publicFunc() public pure returns (string memory) {
        return "Anyone can call me";
    }

    function externalFunc() external pure returns (string memory) {
        return "Only externally callable";
    }

    function internalFunc() internal pure returns (string memory) {
        return "Only this contract and children";
    }

    function privateFunc() private pure returns (string memory) {
        return "Only this contract";
    }

    // State mutability
    function pureFunc(uint256 a, uint256 b) public pure returns (uint256) {
        return a + b;  // Doesn't read or write state
    }

    function viewFunc() public view returns (address) {
        return owner;  // Reads but doesn't write state
    }

    function payableFunc() public payable {
        // Can receive ETH
        emit Received(msg.sender, msg.value);
    }

    function defaultFunc() public returns (uint256) {
        counter++;
        return counter;  // Can read AND write state
    }
}
```

### Modifiers

```solidity
contract ModifierDemo {
    address public owner;
    uint256 public unlockTime;

    constructor() {
        owner = msg.sender;
    }

    // Access control modifier
    modifier onlyOwner() {
        require(msg.sender == owner, "Not the owner");
        _;  // Executes the function body
    }

    // With parameters
    modifier afterTime(uint256 timestamp) {
        require(block.timestamp >= timestamp, "Too early");
        _;
    }

    // With custom validation
    modifier validAddress(address addr) {
        require(addr != address(0), "Zero address");
        require(addr != address(this), "Contract address");
        _;
    }

    // Guard pattern
    modifier nonReentrant() {
        require(!locked, "Reentrancy");
        locked = true;
        _;
        locked = false;
    }

    // Usage
    function withdraw() public onlyOwner {
        payable(owner).transfer(address(this).balance);
    }

    function setTime(uint256 _time) public onlyOwner {
        unlockTime = _time;
    }

    function claim() public afterTime(unlockTime) {
        // Logic
    }

    // Modifier with parameters
    modifier costs(uint256 amount) {
        require(msg.value >= amount, "Not enough ETH");
        _;
        if (msg.value > amount) {
            payable(msg.sender).transfer(msg.value - amount);
        }
    }

    function buyItem() public payable costs(0.1 ether) {
        // Item logic
    }

    bool private locked;
}
```

### Events

```solidity
contract EventDemo {
    // Declare events with indexed parameters for filtering
    event Transfer(
        address indexed from,
        address indexed to,
        uint256 value
    );

    event Approval(
        address indexed owner,
        address indexed spender,
        uint256 value
    );

    event UserRegistered(
        address indexed user,
        string name,
        uint256 timestamp
    );

    // Anonymous event (saves gas, but harder to filter)
    event LogDeposit(address indexed user, uint256 amount) anonymous;

    mapping(address => uint256) public balance;

    function transfer(address to, uint256 amount) public {
        require(balance[msg.sender] >= amount, "Insufficient balance");
        balance[msg.sender] -= amount;
        balance[to] += amount;
        emit Transfer(msg.sender, to, amount);
    }

    function register(string calldata name) public {
        emit UserRegistered(msg.sender, name, block.timestamp);
    }
}
```

### Libraries

```solidity
// SafeMath (unnecessary after Solidity 0.8, but shows pattern)
library SafeMath {
    function add(uint256 a, uint256 b) internal pure returns (uint256) {
        uint256 c = a + b;
        require(c >= a, "SafeMath: addition overflow");
        return c;
    }

    function sub(uint256 a, uint256 b) internal pure returns (uint256) {
        require(b <= a, "SafeMath: subtraction underflow");
        return a - b;
    }

    function mul(uint256 a, uint256 b) internal pure returns (uint256) {
        if (a == 0) return 0;
        uint256 c = a * b;
        require(c / a == b, "SafeMath: multiplication overflow");
        return c;
    }

    function div(uint256 a, uint256 b) internal pure returns (uint256) {
        require(b > 0, "SafeMath: division by zero");
        return a / b;
    }
}

// Usage
contract MathContract {
    using SafeMath for uint256;

    function calculate(uint256 a, uint256 b) public pure returns (uint256) {
        return a.add(b).mul(b).div(a);
    }
}

// Reusable library
library AddressUtils {
    function isContract(address account) internal view returns (bool) {
        uint256 size;
        assembly {
            size := extcodesize(account)
        }
        return size > 0;
    }

    function toPayable(address account) internal pure returns (address payable) {
        return payable(account);
    }

    function sendValue(address payable recipient, uint256 amount) internal {
        require(address(this).balance >= amount, "Insufficient balance");
        (bool success, ) = recipient.call{value: amount}("");
        require(success, "Transfer failed");
    }
}
```

## 2. Gas Optimization

### Optimization Techniques

```solidity
pragma solidity ^0.8.20;

contract GasOptimization {
    // BAD: Wastes gas
    string public name = "DefaultName";
    uint256 public total;

    function badLoop(uint256[] memory data) public {
        for (uint256 i = 0; i < data.length; i++) {
            total += data[i];
        }
    }

    // GOOD: Cache array length
    function goodLoop(uint256[] memory data) public {
        uint256 len = data.length;
        for (uint256 i = 0; i < len; i++) {
            total += data[i];
        }
    }

    // BAD: Unbounded loops
    mapping(uint256 => address) public largeMapping;

    function badUpdateAll() public {
        for (uint256 i = 0; i < 10000; i++) {
            largeMapping[i] = msg.sender;
        }
    }

    // GOOD: Use packing (uint256 -> uint128 + uint128)
    struct Unpacked {
        uint256 a;  // 256 bits  | 32 bytes
        uint256 b;  // 256 bits  | 32 bytes
        uint256 c;  // 256 bits  | 32 bytes
        uint256 d;  // 256 bits  | 32 bytes
    }
    // Total: 4 slots (128 bytes)

    struct Packed {
        uint128 a;  // 128 bits  | 16 bytes
        uint128 b;  // 128 bits  | 16 bytes
        uint128 c;  // 128 bits  | 16 bytes
        uint128 d;  // 128 bits  | 16 bytes
    }
    // Total: 2 slots (64 bytes)

    // BAD: Separate variables that could be packed
    uint128 public x;  // slot 1 (16 bytes used)
    uint128 public y;  // slot 2 (16 bytes used)
    uint256 public z;  // slot 3 (32 bytes used)

    // GOOD: Pack related variables
    uint128 public x2;
    uint128 public y2;
    uint256 public z2;  // x2 and y2 share slot 1, z2 in slot 2

    // BAD: Using string when bytes32 works
    string public constant BAD_STATUS = "ACTIVE";

    // GOOD: Use bytes32 for fixed-size data
    bytes32 public constant STATUS = "ACTIVE";

    // BAD: Sload repeated reads
    function badRead() public view returns (uint256) {
        uint256 val = total + total + total; // reads 'total' 3 times
        return val;
    }

    // GOOD: Cache storage reads
    function goodRead() public view returns (uint256) {
        uint256 cached = total; // one SLOAD
        uint256 val = cached + cached + cached;
        return val;
    }

    // BAD: Writing unchanged storage
    function badWrite(uint256 _val) public {
        // Even if _val == total, this writes to storage (costs gas)
        total = _val;
    }

    // GOOD: Check before write
    function goodWrite(uint256 _val) public {
        if (total != _val) {
            total = _val;
        }
    }

    // Use calldata instead of memory for external function params
    function processArray(uint256[] calldata data) external pure returns (uint256) {
        // calldata is read-only and cheaper than memory
        uint256 sum;
        for (uint256 i = 0; i < data.length; i++) {
            sum += data[i];
        }
        return sum;
    }

    // Use uint256 exclusively (cheaper than smaller types due to EVM word size)
    // Unless packing in structs

    // Short-circuit conditions
    function validate(address user, uint256 amount) public view returns (bool) {
        // Place cheaper check first
        return amount > 0 && user != address(0);
    }

    // Unchecked blocks for operations that won't overflow
    function sumArray(uint256[] calldata data) external pure returns (uint256 total) {
        uint256 len = data.length;
        unchecked {
            for (uint256 i; i < len; ++i) {
                total += data[i];
            }
        }
    }
}
```

### Gas Costs Reference

| Operation | Gas | Notes |
|---|---|---|
| SLOAD (warm) | 100 | Reading storage slot recently accessed |
| SLOAD (cold) | 2100 | Reading storage slot first time |
| SSTORE (0->nonzero) | 22100 | Setting storage from 0 |
| SSTORE (nonzero->nonzero) | 2900 | Updating existing storage value |
| SSTORE (nonzero->0) | 5000 + 15000 refund | Clearing storage |
| BALANCE | 2600 | Reading ETH balance |
| CALL (with value) | 9000 + 6700 | External call sending ETH |
| CALL (without value) | 700 | External call |
| LOG0 | 375 + 8/byte | Event without topics |
| LOG1 | 375 + 8/byte + 375 | Event with 1 topic |
| LOG2 | 375 + 8/byte + 750 | Event with 2 topics |
| SHA3 | 30 + 6/word | keccak256 hashing |
| ADD/SUB | 3 | Arithmetic |
| MUL/DIV | 5 | Arithmetic |
| JUMP | 8 | Jump opcode |
| SLOAD->SSTORE in same tx | 100 + 2900 | Dirty slot behavior |

## 3. Smart Contract Security

### Common Vulnerabilities

```solidity
// 1. Reentrancy
contract VulnerableBank {
    mapping(address => uint256) public balances;

    // VULNERABLE: External call before state change
    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient");
        (bool success, ) = msg.sender.call{value: amount}(""); // External call
        require(success);
        balances[msg.sender] -= amount; // State change AFTER call
    }

    // FIX: Use Checks-Effects-Interactions pattern
    function safeWithdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient");
        balances[msg.sender] -= amount; // Effect first
        (bool success, ) = msg.sender.call{value: amount}(""); // Interaction
        require(success);
    }

    // FIX: Use ReentrancyGuard
    bool private locked;
    modifier noReentrant() {
        require(!locked, "Reentrancy detected");
        locked = true;
        _;
        locked = false;
    }

    function secureWithdraw(uint256 amount) public noReentrant {
        require(balances[msg.sender] >= amount);
        uint256 bal = balances[msg.sender];
        balances[msg.sender] = 0; // CEI
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success);
    }
}

// 2. Integer Overflow/Underflow (pre-Solidity 0.8)
contract Overflow {
    // Pre-0.8: Use SafeMath. Post-0.8: checked by default.
    uint8 public small = 0;

    function badDecrement() public {
        // Reverts in 0.8+ because of underflow check
        small--;
    }

    function uncheckedDecrement() public {
        unchecked {
            small--; // Wraps from 0 to 255 (if you need this behavior)
        }
    }
}

// 3. Access Control Issues
contract AccessControl {
    address public owner;

    // BAD: Missing modifier
    function changeOwner(address newOwner) public {
        owner = newOwner; // Anyone can call!
    }

    // GOOD: Proper access control
    modifier onlyOwner() {
        require(msg.sender == owner, "Unauthorized");
        _;
    }
    function safeChangeOwner(address newOwner) public onlyOwner {
        owner = newOwner;
    }

    // Use Ownable from OpenZeppelin
    // import "@openzeppelin/contracts/access/Ownable.sol";
    // contract MyContract is Ownable { ... }
}

// 4. Front-running
contract FrontRunningVulnerable {
    mapping(address => uint256) public pendingWithdrawals;

    function withdraw() public {
        // Attacker can observe tx in mempool and front-run
        uint256 amount = pendingWithdrawals[msg.sender];
        pendingWithdrawals[msg.sender] = 0;
        payable(msg.sender).transfer(amount);
    }

    // Mitigation: commit-reveal scheme or submarine sends
}

// 5. Timestamp Dependence
contract TimestampDependence {
    // BAD: block.timestamp can be manipulated by miners
    function random() public view returns (uint256) {
        return uint256(keccak256(abi.encodePacked(block.timestamp))) % 100;
    }

    // BETTER: Use block.prevrandao (post-merge) + nonce
    // BEST: Use Chainlink VRF for randomness
}

// 6. Unchecked External Calls
contract UncheckedCall {
    function badTransfer(address to, uint256 amount) public {
        to.call{value: amount}(""); // Not checked!
    }

    function goodTransfer(address payable to, uint256 amount) public {
        (bool success, ) = to.call{value: amount}("");
        require(success, "Transfer failed");
    }
}

// 7. Delegatecall Issues
contract Proxy {
    address public implementation;

    // DANGEROUS: delegatecall to arbitrary address
    function delegate(address target, bytes calldata data) external {
        (bool success, ) = target.delegatecall(data);
        require(success);
    }

    // Always use a known implementation and verify it
    function upgrade(address newImpl) public onlyOwner {
        require(newImpl != address(0), "Zero address");
        require(AddressUtils.isContract(newImpl), "Not a contract");
        implementation = newImpl;
    }
}
```

### Security Checklist

| Item | Check |
|---|---|
| CEI pattern | State changes before external calls |
| Reentrancy guard | noReentrant on withdrawal functions |
| Access control | onlyOwner, role-based controls |
| Input validation | All user inputs validated |
| Integer overflow | Solidity 0.8+ default checks |
| Oracle manipulation | Use decentralized oracles (Chainlink) |
| Flash loan attacks | Check price manipulation in lending |
| Signature replay | Include nonce + chainId in EIP-712 |
| Selfdestruct | No funds from forced ETH sends |
| Randomness | Use Chainlink VRF, not block values |
| Upgradeability | Transparent/ UUPS proxy patterns |
| Circuit breaker | Emergency pause mechanism |

## 4. Token Standards

### ERC-20 (Fungible Token)

```solidity
// Minimal ERC-20 implementation
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract MyToken is ERC20, Ownable {
    uint256 public constant MAX_SUPPLY = 1_000_000 * 10**18;

    constructor() ERC20("MyToken", "MTK") {
        _mint(msg.sender, 100_000 * 10**18); // Initial supply
    }

    function mint(address to, uint256 amount) external onlyOwner {
        require(totalSupply() + amount <= MAX_SUPPLY, "Exceeds max supply");
        _mint(to, amount);
    }

    function burn(uint256 amount) external {
        _burn(msg.sender, amount);
    }

    // Override to add logic
    function _beforeTokenTransfer(
        address from, address to, uint256 amount
    ) internal override {
        require(to != address(0) || from != address(0), "Zero address");
        super._beforeTokenTransfer(from, to, amount);
    }

    // Snapshot mechanism (OpenZeppelin ERC20Snapshot)
}
```

### ERC-721 (NFT)

```solidity
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

contract MyNFT is ERC721URIStorage, Ownable {
    using Counters for Counters.Counter;
    Counters.Counter private _tokenIds;

    uint256 public mintPrice = 0.01 ether;
    uint256 public maxSupply = 10000;
    string public baseURI;

    constructor() ERC721("MyNFT", "MNFT") {}

    function mint(string memory tokenURI) external payable {
        require(msg.value >= mintPrice, "Insufficient payment");
        require(_tokenIds.current() < maxSupply, "Max supply reached");

        _tokenIds.increment();
        uint256 newTokenId = _tokenIds.current();
        _safeMint(msg.sender, newTokenId);
        _setTokenURI(newTokenId, tokenURI);
    }

    function withdraw() external onlyOwner {
        payable(owner()).transfer(address(this).balance);
    }

    function setBaseURI(string memory _baseURI) external onlyOwner {
        baseURI = _baseURI;
    }

    // Override to use base URI
    function _baseURI() internal view override returns (string memory) {
        return baseURI;
    }

    // Royalty support (ERC-2981)
    function royaltyInfo(uint256 tokenId, uint256 salePrice)
        external view returns (address receiver, uint256 amount)
    {
        return (owner(), salePrice / 10); // 10% royalty
    }
}
```

### ERC-1155 (Multi-Token)

```solidity
import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

contract GameItems is ERC1155, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant BURNER_ROLE = keccak256("BURNER_ROLE");

    // Token types
    uint256 public constant SWORD = 0;
    uint256 public constant SHIELD = 1;
    uint256 public constant POTION = 2;
    uint256 public constant GOLD = 3;

    string public name = "Game Items";
    string public symbol = "GAME";

    constructor() ERC1155("https://game.example/api/items/{id}.json") {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);

        // Mint initial items
        _mint(msg.sender, SWORD, 100, "");
        _mint(msg.sender, SHIELD, 50, "");
        _mint(msg.sender, POTION, 1000, "");
    }

    function mint(address to, uint256 id, uint256 amount) external onlyRole(MINTER_ROLE) {
        _mint(to, id, amount, "");
    }

    function mintBatch(address to, uint256[] memory ids, uint256[] memory amounts)
        external onlyRole(MINTER_ROLE)
    {
        _mintBatch(to, ids, amounts, "");
    }

    function burn(address from, uint256 id, uint256 amount) external onlyRole(BURNER_ROLE) {
        _burn(from, id, amount);
    }

    // Override required for AccessControl
    function supportsInterface(bytes4 interfaceId)
        public view override(ERC1155, AccessControl) returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
```

## 5. Web3.js & Ethers.js

### Ethers.js

```typescript
import { ethers } from "ethers";

// Connect to provider
const provider = new ethers.JsonRpcProvider(process.env.RPC_URL);
const wallet = new ethers.Wallet(process.env.PRIVATE_KEY, provider);
const signer = wallet.connect(provider);

// Contract interaction
const ABI = [
    "function balanceOf(address) view returns (uint256)",
    "function transfer(address to, uint256 amount) returns (bool)",
    "event Transfer(address indexed from, address indexed to, uint256 value)",
];
const contract = new ethers.Contract("0x...", ABI, signer);

// Read
const balance = await contract.balanceOf("0x...");
console.log(`Balance: ${ethers.formatEther(balance)}`);

// Write (send transaction)
const tx = await contract.transfer("0x...", ethers.parseEther("10"));
console.log(`Tx hash: ${tx.hash}`);
await tx.wait(); // Wait for confirmation

// Events
contract.on("Transfer", (from, to, value) => {
    console.log(`${from} -> ${to}: ${ethers.formatEther(value)} ETH`);
});

// Filter events
const filter = contract.filters.Transfer("0xFromAddress");
const events = await contract.queryFilter(filter, 18000000, "latest");

// ENS resolution
const address = await provider.resolveName("vitalik.eth");
const ens = await provider.lookupAddress("0x...");

// Gas estimation
const gasEstimate = await contract.transfer.estimateGas("0x...", ethers.parseEther("1"));
const gasPrice = await provider.getFeeData();

// EIP-1559 transaction
const tx2 = await signer.sendTransaction({
    to: "0x...",
    value: ethers.parseEther("0.1"),
    maxFeePerGas: gasPrice.maxFeePerGas,
    maxPriorityFeePerGas: gasPrice.maxPriorityFeePerGas,
});

// Encoding/Decoding
const funcData = contract.interface.encodeFunctionData("transfer", ["0x...", ethers.parseEther("1")]);
const decoded = contract.interface.decodeFunctionResult("balanceOf", "0x...");

// EIP-712 typed data signing
const domain = {
    name: "MyDApp",
    version: "1",
    chainId: 1,
    verifyingContract: "0x...",
};
const types = {
    Transfer: [
        { name: "from", type: "address" },
        { name: "to", type: "address" },
        { name: "amount", type: "uint256" },
    ],
};
const value = { from: "0x...", to: "0x...", amount: 1000 };
const signature = await wallet.signTypedData(domain, types, value);
```

### Web3.js

```javascript
const Web3 = require('web3');
const web3 = new Web3(process.env.RPC_URL);

// Account
const account = web3.eth.accounts.privateKeyToAccount(process.env.PRIVATE_KEY);
web3.eth.accounts.wallet.add(account);

// Contract
const contract = new web3.eth.Contract(ABI, "0x...");

// Call (read)
const balance = await contract.methods.balanceOf("0x...").call();

// Send (write)
const receipt = await contract.methods.transfer("0x...", "1000000000000000000")
    .send({ from: account.address, gas: 50000 });

// Estimate gas
const gas = await contract.methods.transfer("0x...", "1").estimateGas({ from: account.address });

// Events
contract.events.Transfer({
    filter: { from: "0x..." },
    fromBlock: 18000000
})
.on('data', event => console.log(event.returnValues))
.on('error', console.error);

// Get past events
const events = await contract.getPastEvents('Transfer', {
    filter: { from: "0x..." },
    fromBlock: 18000000,
    toBlock: 'latest'
});

// Batch requests
const batch = new web3.BatchRequest();
batch.add(web3.eth.getBalance.request("0x...", null, (err, bal) => {}));
batch.add(web3.eth.getTransactionCount.request("0x...", (err, count) => {}));
batch.execute();
```

## 6. Hardhat & Foundry

### Hardhat Project Setup

```javascript
// hardhat.config.js
require("@nomicfoundation/hardhat-toolbox");
require("@openzeppelin/hardhat-upgrades");
require("hardhat-gas-reporter");
require("solidity-coverage");

module.exports = {
    solidity: {
        version: "0.8.20",
        settings: {
            optimizer: { enabled: true, runs: 200 },
            viaIR: true,
        },
    },
    networks: {
        hardhat: {
            chainId: 31337,
            forking: {
                url: process.env.MAINNET_RPC_URL,
                blockNumber: 18000000,
            },
        },
        sepolia: {
            url: process.env.SEPOLIA_RPC_URL,
            accounts: [process.env.PRIVATE_KEY],
        },
        mainnet: {
            url: process.env.MAINNET_RPC_URL,
            accounts: [process.env.PRIVATE_KEY],
        },
    },
    etherscan: {
        apiKey: process.env.ETHERSCAN_API_KEY,
    },
    gasReporter: {
        enabled: true,
        currency: "USD",
        coinmarketcap: process.env.COINMARKETCAP_API_KEY,
    },
};
```

### Hardhat Tests

```typescript
// test/Token.test.ts
import { expect } from "chai";
import { ethers } from "hardhat";

describe("MyToken", function () {
    async function deployFixture() {
        const [owner, addr1, addr2] = await ethers.getSigners();
        const Token = await ethers.getContractFactory("MyToken");
        const token = await Token.deploy();
        return { token, owner, addr1, addr2 };
    }

    it("should deploy with correct name", async function () {
        const { token } = await deployFixture();
        expect(await token.name()).to.equal("MyToken");
    });

    it("should assign initial supply to owner", async function () {
        const { token, owner } = await deployFixture();
        const supply = await token.totalSupply();
        const balance = await token.balanceOf(owner.address);
        expect(balance).to.equal(supply);
    });

    it("should transfer tokens between accounts", async function () {
        const { token, owner, addr1 } = await deployFixture();
        await token.transfer(addr1.address, ethers.parseEther("100"));
        const addr1Balance = await token.balanceOf(addr1.address);
        expect(addr1Balance).to.equal(ethers.parseEther("100"));
    });

    it("should reject transfers exceeding balance", async function () {
        const { token, addr1, addr2 } = await deployFixture();
        await expect(
            token.connect(addr1).transfer(addr2.address, ethers.parseEther("1"))
        ).to.be.revertedWith("ERC20: insufficient allowance");
    });

    it("should handle allowance correctly", async function () {
        const { token, owner, addr1, addr2 } = await deployFixture();
        await token.approve(addr1.address, ethers.parseEther("50"));
        await token.connect(addr1).transferFrom(owner.address, addr2.address, ethers.parseEther("50"));
        const addr2Balance = await token.balanceOf(addr2.address);
        expect(addr2Balance).to.equal(ethers.parseEther("50"));
    });

    // Testing events
    it("should emit Transfer event", async function () {
        const { token, owner, addr1 } = await deployFixture();
        await expect(token.transfer(addr1.address, ethers.parseEther("10")))
            .to.emit(token, "Transfer")
            .withArgs(owner.address, addr1.address, ethers.parseEther("10"));
    });
});
```

### Foundry (Forge)

```solidity
// src/Counter.sol
contract Counter {
    uint256 public number;

    function setNumber(uint256 newNumber) public {
        number = newNumber;
    }

    function increment() public {
        number++;
    }
}
```

```solidity
// test/Counter.t.sol
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/Counter.sol";

contract CounterTest is Test {
    Counter public counter;

    function setUp() public {
        counter = new Counter();
        counter.setNumber(10);
    }

    function testIncrement() public {
        counter.increment();
        assertEq(counter.number(), 11);
    }

    function testSetNumber() public {
        counter.setNumber(42);
        assertEq(counter.number(), 42);
    }

    function testFuzzSetNumber(uint256 x) public {
        counter.setNumber(x);
        assertEq(counter.number(), x);
    }

    function testFailIncrementOverflow() public {
        counter.setNumber(type(uint256).max);
        counter.increment(); // Should revert
    }

    // Gas usage assertion
    function testGasIncrement() public {
        uint256 gasStart = gasleft();
        counter.increment();
        uint256 gasUsed = gasStart - gasleft();
        assertLt(gasUsed, 50000); // Under 50k gas
    }

    // Fork testing
    function testForkMainnet() public {
        vm.createSelectFork(vm.envString("MAINNET_RPC_URL"));
        // Interact with mainnet contracts
    }
}
```

```bash
# Forge commands
forge build
forge test
forge test --match-test testFuzz -vvv
forge coverage
forge snapshot
forge inspect Counter storage
forge script DeployScript --rpc-url sepolia --broadcast -vvv

# Cast (on-chain interaction)
cast balance 0x...
cast call 0x... "balanceOf(address)(uint256)" 0x...
cast send 0x... "transfer(address,uint256)" 0x... 1000 --private-key $PK
cast block latest
cast sig "transfer(address,uint256)"
```

## 7. DeFi (Decentralized Finance)

### AMM (Automated Market Maker)

```solidity
// Constant Product AMM (like Uniswap V2)
// x * y = k
contract SimpleAMM {
    IERC20 public token0;
    IERC20 public token1;
    uint256 public reserve0;
    uint256 public reserve1;

    event Swap(address indexed user, uint256 amount0Out, uint256 amount1Out);
    event LiquidityAdded(address indexed user, uint256 amount0, uint256 amount1);
    event LiquidityRemoved(address indexed user, uint256 amount0, uint256 amount1);

    constructor(address _token0, address _token1) {
        token0 = IERC20(_token0);
        token1 = IERC20(_token1);
    }

    function addLiquidity(uint256 amount0, uint256 amount1) external {
        require(amount0 > 0 && amount1 > 0, "Zero amounts");

        token0.transferFrom(msg.sender, address(this), amount0);
        token1.transferFrom(msg.sender, address(this), amount1);

        reserve0 += amount0;
        reserve1 += amount1;

        emit LiquidityAdded(msg.sender, amount0, amount1);
    }

    function swap(address tokenIn, uint256 amountIn) external returns (uint256 amountOut) {
        require(amountIn > 0, "Zero amount in");

        (uint256 r0, uint256 r1) = (reserve0, reserve1);
        bool isToken0 = tokenIn == address(token0);

        // x * y = k
        uint256 amountInWithFee = amountIn * 997; // 0.3% fee
        uint256 numerator;

        if (isToken0) {
            numerator = amountInWithFee * r1;
            amountOut = numerator / (r0 * 1000 + amountInWithFee);
            token0.transferFrom(msg.sender, address(this), amountIn);
            token1.transfer(msg.sender, amountOut);
            reserve0 += amountIn;
            reserve1 -= amountOut;
        } else {
            numerator = amountInWithFee * r0;
            amountOut = numerator / (r1 * 1000 + amountInWithFee);
            token1.transferFrom(msg.sender, address(this), amountIn);
            token0.transfer(msg.sender, amountOut);
            reserve1 += amountIn;
            reserve0 -= amountOut;
        }

        emit Swap(msg.sender, isToken0 ? amountIn : amountOut, isToken0 ? amountOut : amountIn);
    }

    function getAmountOut(uint256 amountIn, uint256 reserveIn, uint256 reserveOut)
        public pure returns (uint256)
    {
        uint256 amountInWithFee = amountIn * 997;
        uint256 numerator = amountInWithFee * reserveOut;
        uint256 denominator = reserveIn * 1000 + amountInWithFee;
        return numerator / denominator;
    }

    function getReserves() public view returns (uint256, uint256) {
        return (reserve0, reserve1);
    }
}
```

### Lending Protocol (Simplified)

```solidity
contract SimpleLending {
    IERC20 public asset;
    uint256 public totalLent;
    uint256 public totalBorrowed;
    uint256 public interestRate = 500; // 5% APR (in basis points)

    mapping(address => uint256) public deposits;
    mapping(address => uint256) public borrows;

    event Deposited(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);
    event Borrowed(address indexed user, uint256 amount);
    event Repaid(address indexed user, uint256 amount);

    constructor(address _asset) {
        asset = IERC20(_asset);
    }

    // Collateral ratio: 150%
    uint256 public constant COLLATERAL_RATIO = 150;

    function deposit(uint256 amount) external {
        asset.transferFrom(msg.sender, address(this), amount);
        deposits[msg.sender] += amount;
        totalLent += amount;
        emit Deposited(msg.sender, amount);
    }

    function withdraw(uint256 amount) external {
        require(deposits[msg.sender] >= amount, "Insufficient deposit");
        require(asset.balanceOf(address(this)) >= totalLent - totalBorrowed, "Insufficient liquidity");

        deposits[msg.sender] -= amount;
        totalLent -= amount;
        asset.transfer(msg.sender, amount);
        emit Withdrawn(msg.sender, amount);
    }

    function borrow(uint256 amount) external {
        uint256 requiredCollateral = (amount * COLLATERAL_RATIO) / 100;
        require(deposits[msg.sender] >= requiredCollateral, "Insufficient collateral");
        require(asset.balanceOf(address(this)) >= amount, "Insufficient liquidity");

        borrows[msg.sender] += amount;
        totalBorrowed += amount;
        asset.transfer(msg.sender, amount);
        emit Borrowed(msg.sender, amount);
    }

    function repay(uint256 amount) external {
        require(borrows[msg.sender] >= amount, "Borrow too low");

        asset.transferFrom(msg.sender, address(this), amount);
        borrows[msg.sender] -= amount;
        totalBorrowed -= amount;
        emit Repaid(msg.sender, amount);
    }

    function calculateInterest(address user) public view returns (uint256) {
        return (borrows[user] * interestRate) / 10000;
    }

    function getHealthFactor(address user) public view returns (uint256) {
        if (borrows[user] == 0) return type(uint256).max;
        return (deposits[user] * 100) / borrows[user];
    }
}
```

### Oracle Integration (Chainlink)

```solidity
import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

contract PriceFeed {
    AggregatorV3Interface internal priceFeed;

    // ETH/USD price feed on Ethereum Mainnet: 0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419
    constructor(address feedAddress) {
        priceFeed = AggregatorV3Interface(feedAddress);
    }

    function getLatestPrice() public view returns (uint256) {
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();

        require(price > 0, "Invalid price");
        require(block.timestamp - updatedAt < 1 hours, "Stale price");

        return uint256(price) * 10**10; // Convert to 18 decimals
    }

    function getDecimals() public view returns (uint8) {
        return priceFeed.decimals();
    }
}
```

## 8. NFTs

### Metadata Structure

```json
{
    "name": "Artwork #42",
    "description": "A unique generative artwork on the blockchain",
    "image": "ipfs://QmXyZ...",
    "external_url": "https://mycollection.xyz/42",
    "animation_url": "ipfs://QmAbc...",
    "attributes": [
        { "trait_type": "Background", "value": "Sunset" },
        { "trait_type": "Color", "value": "Blue" },
        { "trait_type": "Rarity", "value": "Legendary" },
        { "display_type": "number", "trait_type": "Generation", "value": 1 },
        { "display_type": "boost_percentage", "trait_type": "Power", "value": 150 },
        { "display_type": "date", "trait_type": "Minted", "value": 1700000000 }
    ]
}
```

### NFT Marketplace

```solidity
contract SimpleMarketplace {
    struct Listing {
        address seller;
        address nftContract;
        uint256 tokenId;
        uint256 price;
        bool active;
    }

    uint256 public listingCounter;
    mapping(uint256 => Listing) public listings;
    mapping(address => mapping(uint256 => uint256)) public activeListing; // nft -> tokenId -> listingId

    event Listed(uint256 indexed listingId, address indexed seller, address indexed nft, uint256 tokenId, uint256 price);
    event Sold(uint256 indexed listingId, address indexed buyer, address indexed seller, uint256 price);
    event Cancelled(uint256 indexed listingId);

    function list(address nftContract, uint256 tokenId, uint256 price) external {
        IERC721(nftContract).transferFrom(msg.sender, address(this), tokenId);
        require(activeListing[nftContract][tokenId] == 0, "Already listed");

        listingCounter++;
        listings[listingCounter] = Listing(msg.sender, nftContract, tokenId, price, true);
        activeListing[nftContract][tokenId] = listingCounter;

        emit Listed(listingCounter, msg.sender, nftContract, tokenId, price);
    }

    function buy(uint256 listingId) external payable {
        Listing storage listing = listings[listingId];
        require(listing.active, "Not active");
        require(msg.value >= listing.price, "Insufficient funds");

        listing.active = false;
        activeListing[listing.nftContract][listing.tokenId] = 0;

        IERC721(listing.nftContract).transferFrom(address(this), msg.sender, listing.tokenId);
        payable(listing.seller).transfer(msg.value);

        emit Sold(listingId, msg.sender, listing.seller, msg.value);
    }

    function cancel(uint256 listingId) external {
        Listing storage listing = listings[listingId];
        require(listing.seller == msg.sender, "Not seller");
        require(listing.active, "Not active");

        listing.active = false;
        activeListing[listing.nftContract][listing.tokenId] = 0;

        IERC721(listing.nftContract).transferFrom(address(this), msg.sender, listing.tokenId);
        emit Cancelled(listingId);
    }
}
```

## 9. Layer 2 Solutions

### Comparison

| Solution | Type | Finality | Security | TPS | Cost |
|---|---|---|---|---|---|
| Optimism | Optimistic Rollup | ~7 days | Fraud proofs | ~2000 | Low |
| Arbitrum | Optimistic Rollup | ~7 days | Fraud proofs | ~2500 | Low |
| zkSync Era | ZK-Rollup | Minutes | Validity proofs | ~3000 | Very low |
| StarkNet | ZK-Rollup | Minutes | Validity proofs | ~10000 | Very low |
| Polygon zkEVM | ZK-Rollup | Minutes | Validity proofs | ~2000 | Very low |
| Base | Optimistic Rollup | ~7 days | Fraud proofs | ~2000 | Low |
| Scroll | ZK-Rollup | Minutes | Validity proofs | ~2000 | Very low |

### Bridge Interaction

```typescript
// Bridge ETH from L1 to L2 (Arbitrum)
import { Bridge } from '@arbitrum/sdk';

async function bridgeETH(l1Provider, l2Provider, wallet, amount: string) {
    const l1Signer = wallet.connect(l1Provider);
    const bridge = await Bridge.init(l1Signer, l2Provider);

    const tx = await bridge.depositETH(
        ethers.parseEther(amount),
        wallet.address  // recipient on L2
    );
    await tx.wait();

    // Wait for L2 arbitration
    const receipt = await tx.waitForL2(l2Provider);
    console.log('Bridged to L2:', receipt.transactionHash);
}

// zkSync bridge
import { Provider, Wallet } from 'zksync-ethers';
import { ethers } from 'ethers';

async function depositToZkSync() {
    const zkSyncProvider = new Provider('https://mainnet.era.zksync.io');
    const ethProvider = ethers.getDefaultProvider('mainnet');
    const wallet = new Wallet(process.env.PRIVATE_KEY, ethProvider, zkSyncProvider);

    const deposit = await wallet.deposit({
        token: ethers.ZeroAddress, // ETH
        amount: ethers.parseEther("0.1"),
    });
    await deposit.waitFinalize();
}
```

## 10. Wallet Integration

### MetaMask (EIP-1193)

```typescript
// Connect MetaMask
async function connectWallet(): Promise<string> {
    if (!window.ethereum) throw new Error("MetaMask not installed");

    const accounts = await window.ethereum.request({
        method: "eth_requestAccounts"
    });

    window.ethereum.on("accountsChanged", (accounts: string[]) => {
        if (accounts.length === 0) {
            // User disconnected
            window.location.reload();
        } else {
            console.log("Account changed:", accounts[0]);
        }
    });

    window.ethereum.on("chainChanged", (chainId: string) => {
        // Reload on chain change
        window.location.reload();
    });

    window.ethereum.on("disconnect", () => {
        console.log("Wallet disconnected");
    });

    return accounts[0];
}

// Switch network
async function switchNetwork(chainId: number) {
    try {
        await window.ethereum.request({
            method: "wallet_switchEthereumChain",
            params: [{ chainId: `0x${chainId.toString(16)}` }],
        });
    } catch (error: any) {
        if (error.code === 4902) {
            // Chain not added — add it
            await window.ethereum.request({
                method: "wallet_addEthereumChain",
                params: [{
                    chainId: `0x${chainId.toString(16)}`,
                    chainName: "My Network",
                    rpcUrls: ["https://rpc.example.com"],
                    nativeCurrency: { name: "ETH", symbol: "ETH", decimals: 18 },
                    blockExplorerUrls: ["https://explorer.example.com"],
                }],
            });
        }
    }
}

// Sign message
async function signMessage(message: string): Promise<string> {
    const accounts = await window.ethereum.request({ method: "eth_accounts" });
    const signature = await window.ethereum.request({
        method: "personal_sign",
        params: [message, accounts[0]],
    });
    return signature;
}

// Send transaction
async function sendETH(to: string, amount: string): Promise<string> {
    const accounts = await window.ethereum.request({ method: "eth_accounts" });
    const txHash = await window.ethereum.request({
        method: "eth_sendTransaction",
        params: [{
            from: accounts[0],
            to: to,
            value: `0x${BigInt(ethers.parseEther(amount)).toString(16)}`,
        }],
    });
    return txHash;
}
```

### WalletConnect

```typescript
import { Web3Modal } from '@web3modal/ethers';
import { EthersAdapter } from '@reown-network/appkit-adapter-ethers';

// Configure
const web3Modal = new Web3Modal({
    projectId: process.env.WALLETCONNECT_PROJECT_ID,
    ethersConfig: defaultConfig({
        metadata: {
            name: "My DApp",
            description: "My DApp description",
            url: "https://myapp.com",
            icons: ["https://myapp.com/icon.png"],
        }
    }),
    chains: [mainnet, sepolia],
});

// Connect
const provider = await web3Modal.connect();
const signer = await provider.getSigner();
const address = await signer.getAddress();

// Disconnect
await web3Modal.disconnect();
```
