import os
import logging
import random
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger("PineconeClient")

# Soft imports to prevent launch failures
try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    HAS_GOOGLE_EMB = True
except ImportError:
    HAS_GOOGLE_EMB = False

try:
    from pinecone import Pinecone, ServerlessSpec
    HAS_PINECONE = True
except ImportError:
    HAS_PINECONE = False

# ============================================================
# LARGE PLACEMENT QUESTION KNOWLEDGE BASE
# Covers: Google, Amazon, Microsoft, TCS, Infosys, Wipro,
#         Meta, Apple, Adobe, Flipkart, Uber, Netflix
# Difficulties: Easy, Medium, Hard
# Topics: Array, Linked List, Tree, DP, Graph, System Design,
#         SQL/Database, Behavioral, Aptitude, String, Stack, Heap
# ============================================================
KNOWLEDGE_SEED = [

    # ======== GOOGLE - Coding ========
    {
        "id": "google-easy-1",
        "question": "🏢 Google Interview – Array (Easy)\n\nGiven an array of integers, find the two numbers such that they add up to a specific target. Return their indices.\n\nExample: nums = [2,7,11,15], target = 9 → Output: [0,1]\n\nConstraint: Each input has exactly one solution. Time: O(N), Space: O(N).",
        "expected_answer": "Use a hashmap. Iterate through nums; for each element check if (target - nums[i]) is in the map. If yes, return [map[target-nums[i]], i]. Otherwise, add nums[i] -> i to the map.\nPython:\n  def twoSum(nums, target):\n      seen = {}\n      for i, n in enumerate(nums):\n          if target - n in seen:\n              return [seen[target - n], i]\n          seen[n] = i",
        "topic": "Array",
        "difficulty": "Easy",
        "company": "Google, Amazon, Meta",
        "type": "Coding"
    },
    {
        "id": "google-easy-2",
        "question": "🏢 Google Interview – String (Easy)\n\nWrite a function to check if a string is a palindrome.\n\nExample: 'racecar' → True, 'hello' → False\n\nConstraint: Ignore case and non-alphanumeric characters.",
        "expected_answer": "Two-pointer approach: use left and right pointers, move inward while characters match.\nPython:\n  def isPalindrome(s):\n      s = ''.join(c.lower() for c in s if c.isalnum())\n      return s == s[::-1]\nTime: O(N), Space: O(1)",
        "topic": "String",
        "difficulty": "Easy",
        "company": "Google, Apple",
        "type": "Coding"
    },
    {
        "id": "google-medium-1",
        "question": "🏢 Google Interview – Tree (Medium)\n\nGiven a binary tree, perform a level-order traversal (BFS). Return the node values level by level as a list of lists.\n\nExample:\n    3\n   / \\\n  9  20\n    /  \\\n   15   7\n→ [[3], [9,20], [15,7]]\n\nTime Complexity target: O(N)",
        "expected_answer": "Use a queue (deque). Add root, then pop from front and add children to queue. Track level by queue size.\nPython:\n  from collections import deque\n  def levelOrder(root):\n      res, q = [], deque([root])\n      while q:\n          level = []\n          for _ in range(len(q)):\n              node = q.popleft()\n              if node:\n                  level.append(node.val)\n                  q.append(node.left)\n                  q.append(node.right)\n          if level: res.append(level)\n      return res\nTime: O(N), Space: O(N)",
        "topic": "Tree",
        "difficulty": "Medium",
        "company": "Google, Amazon, Microsoft",
        "type": "Coding"
    },
    {
        "id": "google-medium-2",
        "question": "🏢 Google Interview – Graph (Medium)\n\nGiven a 2D grid of '1's (land) and '0's (water), count the number of islands. An island is surrounded by water and formed by connecting adjacent lands horizontally or vertically.\n\nExample:\ngrid = [\n  ['1','1','0','0','0'],\n  ['1','1','0','0','0'],\n  ['0','0','1','0','0'],\n  ['0','0','0','1','1']\n]\n→ Output: 3\n\nTime: O(M×N)",
        "expected_answer": "DFS/BFS flood fill: iterate each cell. When a '1' is found, increment count and DFS to mark all connected '1's as '0'.\nPython:\n  def numIslands(grid):\n      count = 0\n      def dfs(r, c):\n          if r<0 or c<0 or r>=len(grid) or c>=len(grid[0]) or grid[r][c]=='0': return\n          grid[r][c] = '0'\n          dfs(r+1,c); dfs(r-1,c); dfs(r,c+1); dfs(r,c-1)\n      for r in range(len(grid)):\n          for c in range(len(grid[0])):\n              if grid[r][c]=='1':\n                  count += 1\n                  dfs(r,c)\n      return count\nTime: O(M×N), Space: O(M×N) stack",
        "topic": "Graph",
        "difficulty": "Medium",
        "company": "Google, Amazon, Meta, Microsoft",
        "type": "Coding"
    },
    {
        "id": "google-hard-1",
        "question": "🏢 Google Interview – DP Hard\n\nGiven a string s and a dictionary of words, return true if s can be segmented into a sequence of one or more dictionary words.\n\nExample: s='leetcode', wordDict=['leet','code'] → True\nExample: s='applepenapple', wordDict=['apple','pen'] → True\n\nConstraint: Time better than O(N^3).",
        "expected_answer": "DP approach: dp[i] = True if s[0:i] can be segmented. Transition: dp[i] = any(dp[j] and s[j:i] in wordSet) for j in range(i).\nPython:\n  def wordBreak(s, wordDict):\n      wset = set(wordDict)\n      dp = [False] * (len(s)+1)\n      dp[0] = True\n      for i in range(1, len(s)+1):\n          for j in range(i):\n              if dp[j] and s[j:i] in wset:\n                  dp[i] = True\n                  break\n      return dp[-1]\nTime: O(N^2), Space: O(N)",
        "topic": "Dynamic Programming",
        "difficulty": "Hard",
        "company": "Google, Amazon",
        "type": "Coding"
    },
    {
        "id": "google-hard-2",
        "question": "🏢 Google Interview – Heap/Priority Queue (Hard)\n\nFind the kth largest element in an unsorted array without sorting the full array.\n\nExample: nums = [3,2,1,5,6,4], k = 2 → Output: 5\n\nOptimal Approach: Use a Min-Heap of size k. Time: O(N log k).",
        "expected_answer": "Use a Min-Heap of size k. Push all elements; when size > k, pop the minimum. The top of the heap is the kth largest.\nPython:\n  import heapq\n  def findKthLargest(nums, k):\n      heap = []\n      for n in nums:\n          heapq.heappush(heap, n)\n          if len(heap) > k:\n              heapq.heappop(heap)\n      return heap[0]\nTime: O(N log k), Space: O(k)\nAlternative: QuickSelect for O(N) average.",
        "topic": "Heap",
        "difficulty": "Hard",
        "company": "Google, Amazon, Meta",
        "type": "Coding"
    },

    # ======== AMAZON - Coding ========
    {
        "id": "amazon-easy-1",
        "question": "🛒 Amazon Interview – Stack (Easy)\n\nGiven a string with parentheses, check if it's valid.\n\nRules: '(' must be closed by ')' in correct order.\nExample: '()[]{}' → True, '(]' → False, '([)]' → False\n\nTime: O(N), Space: O(N)",
        "expected_answer": "Use a stack. Push open brackets. For closing brackets, check if stack top matches.\nPython:\n  def isValid(s):\n      stack = []\n      match = {')':'(', ']':'[', '}':'{'}\n      for c in s:\n          if c in '([{':\n              stack.append(c)\n          elif not stack or stack[-1] != match[c]:\n              return False\n          else:\n              stack.pop()\n      return len(stack) == 0\nTime: O(N), Space: O(N)",
        "topic": "Stack",
        "difficulty": "Easy",
        "company": "Amazon, Google, Microsoft",
        "type": "Coding"
    },
    {
        "id": "amazon-easy-2",
        "question": "🛒 Amazon Interview – Array (Easy)\n\nRotate an array to the right by k steps.\nExample: nums = [1,2,3,4,5,6,7], k = 3 → [5,6,7,1,2,3,4]\n\nDo it in-place with O(1) extra space.",
        "expected_answer": "Three-reversal trick:\n1. Reverse entire array\n2. Reverse first k elements\n3. Reverse remaining n-k elements\nPython:\n  def rotate(nums, k):\n      n = len(nums)\n      k %= n\n      nums.reverse()\n      nums[:k] = reversed(nums[:k])\n      nums[k:] = reversed(nums[k:])\nTime: O(N), Space: O(1)",
        "topic": "Array",
        "difficulty": "Easy",
        "company": "Amazon, Microsoft",
        "type": "Coding"
    },
    {
        "id": "amazon-medium-1",
        "question": "🛒 Amazon Interview – Linked List (Medium)\n\nReverse a singly linked list.\nExtension: Can you do it iteratively AND recursively?\n\nExample: 1→2→3→4→5 → 5→4→3→2→1\n\nTime: O(N), Space: O(1) for iterative.",
        "expected_answer": "Iterative: use prev, curr pointers.\nPython:\n  def reverseList(head):\n      prev, curr = None, head\n      while curr:\n          nxt = curr.next\n          curr.next = prev\n          prev = curr\n          curr = nxt\n      return prev\n\nRecursive:\n  def reverseList(head):\n      if not head or not head.next: return head\n      new_head = reverseList(head.next)\n      head.next.next = head\n      head.next = None\n      return new_head\nTime: O(N), Space: O(1) iterative / O(N) recursive (call stack)",
        "topic": "Linked List",
        "difficulty": "Medium",
        "company": "Amazon, Microsoft, TCS",
        "type": "Coding"
    },
    {
        "id": "amazon-medium-2",
        "question": "🛒 Amazon Interview – Binary Search (Medium)\n\nSearch an element in a rotated sorted array.\nExample: nums = [4,5,6,7,0,1,2], target = 0 → index 4\nExample: nums = [4,5,6,7,0,1,2], target = 3 → -1\n\nTime: O(log N) required.",
        "expected_answer": "Modified binary search: determine which half is sorted, then check if target is in that sorted half.\nPython:\n  def search(nums, target):\n      l, r = 0, len(nums)-1\n      while l <= r:\n          mid = (l+r)//2\n          if nums[mid] == target: return mid\n          if nums[l] <= nums[mid]:  # left sorted\n              if nums[l] <= target < nums[mid]: r = mid-1\n              else: l = mid+1\n          else:  # right sorted\n              if nums[mid] < target <= nums[r]: l = mid+1\n              else: r = mid-1\n      return -1\nTime: O(log N), Space: O(1)",
        "topic": "Binary Search",
        "difficulty": "Medium",
        "company": "Amazon, Google, Microsoft",
        "type": "Coding"
    },
    {
        "id": "amazon-hard-1",
        "question": "🛒 Amazon Interview – DP Hard\n\nGiven a rod of length n and an array prices where prices[i] is the price of a rod of length i+1, find the maximum obtainable value by cutting up the rod and selling the pieces.\n\nExample: n=4, prices=[1,5,8,9] → 10 (cut into two pieces of length 2)\n\nTime: O(N^2)",
        "expected_answer": "DP: dp[i] = max revenue from rod of length i.\ndp[i] = max(prices[j] + dp[i-j-1]) for j in 0..i-1\nPython:\n  def rodCutting(prices, n):\n      dp = [0] * (n+1)\n      for i in range(1, n+1):\n          for j in range(i):\n              dp[i] = max(dp[i], prices[j] + dp[i-j-1])\n      return dp[n]\nTime: O(N^2), Space: O(N)",
        "topic": "Dynamic Programming",
        "difficulty": "Hard",
        "company": "Amazon",
        "type": "Coding"
    },

    # ======== MICROSOFT - Coding ========
    {
        "id": "microsoft-easy-1",
        "question": "🖥️ Microsoft Interview – String (Easy)\n\nGiven two strings s and t, return true if t is an anagram of s, and false otherwise.\n\nExample: s='anagram', t='nagaram' → True\nExample: s='rat', t='car' → False\n\nTime: O(N), Space: O(1) (fixed 26 chars)",
        "expected_answer": "Count character frequencies. Use an array of 26 integers.\nPython:\n  def isAnagram(s, t):\n      if len(s) != len(t): return False\n      count = [0] * 26\n      for a, b in zip(s, t):\n          count[ord(a)-ord('a')] += 1\n          count[ord(b)-ord('a')] -= 1\n      return all(c == 0 for c in count)\nAlternatively: return sorted(s) == sorted(t) [O(N log N)]",
        "topic": "String",
        "difficulty": "Easy",
        "company": "Microsoft, Google, Amazon",
        "type": "Coding"
    },
    {
        "id": "microsoft-medium-1",
        "question": "🖥️ Microsoft Interview – Tree (Medium)\n\nFind the lowest common ancestor (LCA) of two nodes p and q in a binary search tree.\n\nExample:\n      6\n     / \\\n    2   8\n   / \\ / \\\n  0  4 7  9\n\nLCA(2, 8) = 6, LCA(2, 4) = 2\n\nKey Insight: Use BST property. Time: O(log N) for balanced BST.",
        "expected_answer": "In BST: if both p and q are smaller than root, go left. If both larger, go right. Else root is LCA.\nPython:\n  def lowestCommonAncestor(root, p, q):\n      while root:\n          if p.val < root.val and q.val < root.val:\n              root = root.left\n          elif p.val > root.val and q.val > root.val:\n              root = root.right\n          else:\n              return root\nTime: O(log N) BST / O(N) general, Space: O(1)",
        "topic": "Tree",
        "difficulty": "Medium",
        "company": "Microsoft, Google, Amazon",
        "type": "Coding"
    },
    {
        "id": "microsoft-hard-1",
        "question": "🖥️ Microsoft Interview – DP Hard (Classic)\n\nGiven an m×n grid with obstacles (0=free, 1=obstacle), count unique paths from top-left to bottom-right. You can only move right or down.\n\nExample:\nobstacleGrid = [[0,0,0],[0,1,0],[0,0,0]] → 2\n\nTime: O(M×N), Space: O(M×N) reducible to O(N)",
        "expected_answer": "DP: dp[i][j] = dp[i-1][j] + dp[i][j-1] if no obstacle, else 0.\nPython:\n  def uniquePathsWithObstacles(grid):\n      m, n = len(grid), len(grid[0])\n      dp = [[0]*n for _ in range(m)]\n      dp[0][0] = 1 if grid[0][0] == 0 else 0\n      for i in range(m):\n          for j in range(n):\n              if grid[i][j] == 1: dp[i][j] = 0\n              elif i == 0 and j > 0: dp[i][j] = dp[i][j-1]\n              elif j == 0 and i > 0: dp[i][j] = dp[i-1][j]\n              elif i > 0 and j > 0: dp[i][j] = dp[i-1][j] + dp[i][j-1]\n      return dp[m-1][n-1]\nTime: O(M×N), Space: O(M×N)",
        "topic": "Dynamic Programming",
        "difficulty": "Hard",
        "company": "Microsoft, Google",
        "type": "Coding"
    },

    # ======== META / FACEBOOK ========
    {
        "id": "meta-medium-1",
        "question": "📘 Meta Interview – Array (Medium)\n\nGiven an unsorted integer array, find the smallest missing positive integer.\n\nExample: [1,2,0] → 3 | [3,4,-1,1] → 2 | [7,8,9,11,12] → 1\n\nChallenge: O(N) time and O(1) extra space.",
        "expected_answer": "Index as hash: place each number n in index n-1. Then scan for first index where arr[i] != i+1.\nPython:\n  def firstMissingPositive(nums):\n      n = len(nums)\n      for i in range(n):\n          while 1 <= nums[i] <= n and nums[nums[i]-1] != nums[i]:\n              nums[nums[i]-1], nums[i] = nums[i], nums[nums[i]-1]\n      for i in range(n):\n          if nums[i] != i+1: return i+1\n      return n+1\nTime: O(N), Space: O(1)",
        "topic": "Array",
        "difficulty": "Hard",
        "company": "Meta, Google",
        "type": "Coding"
    },

    # ======== TCS - Coding & Aptitude ========
    {
        "id": "tcs-easy-1",
        "question": "🏭 TCS Interview – Array (Easy)\n\nFind the second largest element in an array without sorting.\n\nExample: [12, 35, 1, 10, 34, 1] → 34\n\nTime: O(N), Space: O(1)",
        "expected_answer": "Track two variables: largest and second_largest.\nPython:\n  def secondLargest(arr):\n      first = second = float('-inf')\n      for n in arr:\n          if n > first:\n              second = first\n              first = n\n          elif n > second and n != first:\n              second = n\n      return second\nTime: O(N), Space: O(1)",
        "topic": "Array",
        "difficulty": "Easy",
        "company": "TCS, Infosys, Wipro",
        "type": "Coding"
    },
    {
        "id": "tcs-aptitude-1",
        "question": "🏭 TCS Aptitude – Train & Time\n\nA train passes a station platform in 36 seconds and a man standing on the platform in 20 seconds. If the speed of the train is 54 km/hr, what is the length of the platform?\n\n(This type of question is common in TCS NQT and campus drives)",
        "expected_answer": "Step 1: Convert speed → 54 × (5/18) = 15 m/s\nStep 2: Length of train = speed × time to pass man = 15 × 20 = 300 m\nStep 3: Train + Platform = 15 × 36 = 540 m\nStep 4: Platform length = 540 - 300 = 240 m\n\nAnswer: 240 meters",
        "topic": "Quantitative Aptitude",
        "difficulty": "Medium",
        "company": "TCS, Infosys, Accenture, Wipro",
        "type": "Aptitude"
    },
    {
        "id": "tcs-aptitude-2",
        "question": "🏭 TCS Aptitude – Percentage\n\nA shopkeeper buys goods at 80% of the marked price and sells at 20% above the marked price. What is the profit percentage?\n\n(Standard TCS campus placement question)",
        "expected_answer": "Let marked price = 100\nCost price = 80\nSelling price = 120\nProfit = 120 - 80 = 40\nProfit % = (40/80) × 100 = 50%\n\nAnswer: 50% profit",
        "topic": "Quantitative Aptitude",
        "difficulty": "Easy",
        "company": "TCS, Infosys",
        "type": "Aptitude"
    },
    {
        "id": "tcs-db-1",
        "question": "🏭 TCS Interview – SQL/Database (Easy)\n\nExplain the difference between PRIMARY KEY and UNIQUE KEY constraints in SQL.\n\nAlso: Can a table have multiple UNIQUE keys? Can it have multiple PRIMARY keys?",
        "expected_answer": "PRIMARY KEY:\n- Uniquely identifies each row\n- Cannot contain NULL values\n- Only ONE per table\n- Creates a clustered index by default\n\nUNIQUE KEY:\n- Also enforces uniqueness\n- CAN contain NULL (one NULL per column in most DBs)\n- A table can have MULTIPLE unique keys\n- Creates a non-clustered index\n\nRule: PRIMARY KEY = NOT NULL + UNIQUE. UNIQUE KEY = just UNIQUE.",
        "topic": "Database Systems",
        "difficulty": "Easy",
        "company": "TCS, Infosys, Wipro, Amazon",
        "type": "Coding"
    },

    # ======== INFOSYS ========
    {
        "id": "infosys-easy-1",
        "question": "🏢 Infosys Interview – Fibonacci (Easy)\n\nPrint the first N Fibonacci numbers. Implement both the recursive approach and the optimized O(N) iterative approach. Explain the difference in time complexity.\n\nExample: N=7 → [0, 1, 1, 2, 3, 5, 8]",
        "expected_answer": "Recursive (exponential, bad for large N):\n  def fib(n): return n if n <= 1 else fib(n-1) + fib(n-2)\n  Time: O(2^N)\n\nIterative (optimal):\n  def fibonacci(n):\n      a, b = 0, 1\n      for _ in range(n):\n          print(a, end=' ')\n          a, b = b, a+b\n  Time: O(N), Space: O(1)\n\nDP with memoization: cache computed values. Time: O(N), Space: O(N)",
        "topic": "Dynamic Programming",
        "difficulty": "Easy",
        "company": "Infosys, TCS, Wipro",
        "type": "Coding"
    },
    {
        "id": "infosys-medium-1",
        "question": "🏢 Infosys Interview – String (Medium)\n\nGiven a string, find the longest palindromic substring.\n\nExample: s='babad' → 'bab' (or 'aba')\nExample: s='cbbd' → 'bb'\n\nTime: O(N^2) or better with Manacher's Algorithm O(N).",
        "expected_answer": "Expand around center approach (O(N^2)):\nFor each index, expand outward as long as characters match.\nPython:\n  def longestPalindrome(s):\n      res = ''\n      def expand(l, r):\n          while l >= 0 and r < len(s) and s[l] == s[r]:\n              l -= 1; r += 1\n          return s[l+1:r]\n      for i in range(len(s)):\n          odd = expand(i, i)\n          even = expand(i, i+1)\n          res = max(res, odd, even, key=len)\n      return res\nTime: O(N^2), Space: O(1)\nOptimal: Manacher's Algorithm → O(N)",
        "topic": "String",
        "difficulty": "Medium",
        "company": "Infosys, Amazon, Google",
        "type": "Coding"
    },

    # ======== WIPRO ========
    {
        "id": "wipro-easy-1",
        "question": "🏭 Wipro Interview – Pattern Logic (Easy)\n\nWrite a program to reverse a number without converting it to a string.\n\nExample: 12345 → 54321, -123 → -321, 1200 → 21\n\nHandle negative numbers. Time: O(digits), Space: O(1).",
        "expected_answer": "Extract digits using modulo and build reversed number:\nPython:\n  def reverse(x):\n      sign = -1 if x < 0 else 1\n      x = abs(x)\n      rev = 0\n      while x:\n          rev = rev * 10 + x % 10\n          x //= 10\n      rev *= sign\n      # Handle overflow for 32-bit\n      if rev < -2**31 or rev > 2**31-1: return 0\n      return rev\nTime: O(log N) — number of digits",
        "topic": "Math",
        "difficulty": "Easy",
        "company": "Wipro, TCS, Infosys",
        "type": "Coding"
    },

    # ======== SYSTEM DESIGN ========
    {
        "id": "sys-rate-limiter",
        "question": "⚙️ System Design – Rate Limiter (Medium)\n\nDesign an API Rate Limiter. Your system should:\n1. Allow N requests per user per minute\n2. Return HTTP 429 Too Many Requests when exceeded\n3. Handle distributed microservices\n\nExplain: Token Bucket vs Leaky Bucket algorithm. Which would you choose for Google Search API?",
        "expected_answer": "Token Bucket:\n- Tokens added at fixed rate (e.g., 10/second)\n- Each request consumes 1 token\n- Allows bursts (when tokens accumulated)\n- Implementation: Redis INCR + TTL\n\nLeaky Bucket:\n- Requests queue up at fixed output rate\n- Smooths bursty traffic\n- Better for consistent throughput\n\nFor Google Search: Token Bucket (allows bursts, user-friendly)\nFor payment APIs: Leaky Bucket (strict rate control)\n\nDistributed: Use Redis with Lua scripts for atomic operations\nKey: rate:{user_id} → counter with TTL\nAlgorithm: Sliding Window Counter for accuracy",
        "topic": "System Design",
        "difficulty": "Medium",
        "company": "Google, Amazon, Netflix, Uber",
        "type": "System Design"
    },
    {
        "id": "sys-design-lru",
        "question": "⚙️ System Design – LRU Cache (Hard)\n\nDesign a data structure that implements an LRU (Least Recently Used) cache.\n\nOperations:\n- get(key): Return value if exists, else -1\n- put(key, value): Insert/update key. Evict LRU if capacity exceeded.\n\nBoth operations must be O(1).",
        "expected_answer": "Use a HashMap + Doubly Linked List:\n- HashMap for O(1) lookup\n- DLL for O(1) insertion/deletion (MRU at head, LRU at tail)\n\nPython (OrderedDict shortcut):\n  from collections import OrderedDict\n  class LRUCache:\n      def __init__(self, capacity):\n          self.cap = capacity\n          self.cache = OrderedDict()\n      def get(self, key):\n          if key not in self.cache: return -1\n          self.cache.move_to_end(key)\n          return self.cache[key]\n      def put(self, key, value):\n          if key in self.cache: self.cache.move_to_end(key)\n          self.cache[key] = value\n          if len(self.cache) > self.cap:\n              self.cache.popitem(last=False)\n\nTime: O(1) both ops, Space: O(capacity)",
        "topic": "System Design",
        "difficulty": "Hard",
        "company": "Amazon, Google, Microsoft, Uber",
        "type": "System Design"
    },

    # ======== BEHAVIORAL ========
    {
        "id": "behav-conflict",
        "question": "🤝 HR/Behavioral – Conflict Resolution\n\nTell me about a time when you had a conflict with a team member during an academic project. How did you resolve it?\n\n(Answer using the STAR method: Situation → Task → Action → Result)\n\nThis is commonly asked at Amazon, Google, Microsoft leadership rounds.",
        "expected_answer": "STAR Method response:\n\nSituation: During my 3rd year project, my team disagreed on whether to use React or Angular for the frontend.\n\nTask: We had 2 weeks to deliver. I needed to ensure we picked the right tech and maintained team morale.\n\nAction: I organized a 30-minute technical review meeting. I asked each member to present pros/cons objectively. Based on our team's existing JavaScript familiarity, we agreed on React.\n\nResult: The project was delivered on time, and the team appreciated the structured decision-making. We scored 92/100.\n\nKey: Show leadership, empathy, and data-driven decision making.",
        "topic": "Behavioral",
        "difficulty": "Easy",
        "company": "Amazon, Google, Microsoft, TCS",
        "type": "Behavioral"
    },
    {
        "id": "behav-leadership",
        "question": "🤝 HR/Behavioral – Leadership\n\nDescribe a time when you led a team under pressure. What was the outcome?\n\nHint: Amazon looks for 'Deliver Results' and 'Bias for Action' leadership principles.\nGoogle looks for 'structured problem solving' and 'learning from failure'.",
        "expected_answer": "Strong answer structure:\n\nSituation: Led a team of 4 for a hackathon with 24-hour deadline.\n\nTask: Build a working prototype for a healthcare IoT app.\n\nAction:\n- Broke down work into parallel tracks (frontend/backend/ML)\n- Set 6-hour checkpoint goals\n- When backend faced database issues at hour 12, I pivoted to mock data to keep frontend moving\n\nResult: Won 2nd place. Product is now being piloted at our college hospital.\n\nKey qualities to demonstrate: Decisiveness, task prioritization, team motivation under pressure.",
        "topic": "Behavioral",
        "difficulty": "Medium",
        "company": "Amazon, Google, Microsoft",
        "type": "Behavioral"
    },

    # ======== ADVANCED DSA ========
    {
        "id": "adv-graph-dijkstra",
        "question": "📐 Advanced – Shortest Path (Hard)\n\nGiven a weighted directed graph, find the shortest path from source to all other vertices using Dijkstra's Algorithm.\n\nExample graph:\n  0→1 (4), 0→2 (1), 2→1 (2), 1→3 (1), 2→3 (5)\nSource = 0\n→ Shortest: [0, 3, 1, 4]\n\nTime: O((V+E) log V) with priority queue.",
        "expected_answer": "Use a min-heap priority queue.\nPython:\n  import heapq\n  def dijkstra(graph, src):\n      dist = {v: float('inf') for v in graph}\n      dist[src] = 0\n      pq = [(0, src)]\n      while pq:\n          d, u = heapq.heappop(pq)\n          if d > dist[u]: continue\n          for v, w in graph[u]:\n              if dist[u] + w < dist[v]:\n                  dist[v] = dist[u] + w\n                  heapq.heappush(pq, (dist[v], v))\n      return dist\nTime: O((V+E) log V), Space: O(V)\nNote: Doesn't work with negative edges → use Bellman-Ford instead.",
        "topic": "Graph",
        "difficulty": "Hard",
        "company": "Google, Amazon, Uber, Flipkart",
        "type": "Coding"
    },
    {
        "id": "adv-dp-lcs",
        "question": "📐 Advanced – LCS (Medium)\n\nGiven two strings s1 and s2, find the length of their Longest Common Subsequence (LCS).\n\nExample: s1='abcde', s2='ace' → 3 (ace)\nExample: s1='abc', s2='abc' → 3\nExample: s1='abc', s2='def' → 0\n\nTime: O(M×N), Space: O(M×N) reducible to O(N).",
        "expected_answer": "2D DP: dp[i][j] = LCS length for s1[:i] and s2[:j]\n- If s1[i-1] == s2[j-1]: dp[i][j] = dp[i-1][j-1] + 1\n- Else: dp[i][j] = max(dp[i-1][j], dp[i][j-1])\nPython:\n  def longestCommonSubsequence(s1, s2):\n      m, n = len(s1), len(s2)\n      dp = [[0]*(n+1) for _ in range(m+1)]\n      for i in range(1, m+1):\n          for j in range(1, n+1):\n              if s1[i-1] == s2[j-1]: dp[i][j] = dp[i-1][j-1]+1\n              else: dp[i][j] = max(dp[i-1][j], dp[i][j-1])\n      return dp[m][n]\nTime: O(M×N), Space: O(M×N)",
        "topic": "Dynamic Programming",
        "difficulty": "Medium",
        "company": "Amazon, Microsoft, Google, Adobe",
        "type": "Coding"
    },
    {
        "id": "adv-sliding-window",
        "question": "📐 Advanced – Sliding Window (Medium)\n\nGiven a string s and a string t, find the minimum window substring of s such that every character in t (including duplicates) is included in the window.\n\nExample: s='ADOBECODEBANC', t='ABC' → 'BANC'\n\nConstraint: O(N) time.",
        "expected_answer": "Sliding window with two frequency maps:\nPython:\n  from collections import Counter\n  def minWindow(s, t):\n      need = Counter(t)\n      have, total = 0, len(need)\n      window = {}\n      res, resLen = [-1,-1], float('inf')\n      l = 0\n      for r in range(len(s)):\n          c = s[r]\n          window[c] = window.get(c, 0) + 1\n          if c in need and window[c] == need[c]:\n              have += 1\n          while have == total:\n              if r-l+1 < resLen:\n                  resLen = r-l+1\n                  res = [l, r]\n              window[s[l]] -= 1\n              if s[l] in need and window[s[l]] < need[s[l]]:\n                  have -= 1\n              l += 1\n      l, r = res\n      return s[l:r+1] if resLen != float('inf') else ''\nTime: O(N), Space: O(|charset|)",
        "topic": "String",
        "difficulty": "Hard",
        "company": "Google, Amazon, Meta",
        "type": "Coding"
    },
]

# ============================================================
# Company alias map for fuzzy matching
# ============================================================
COMPANY_ALIASES = {
    "google": ["google"],
    "amazon": ["amazon"],
    "microsoft": ["microsoft"],
    "meta": ["meta", "facebook"],
    "tcs": ["tcs", "tata", "tata consultancy"],
    "infosys": ["infosys"],
    "wipro": ["wipro"],
    "uber": ["uber"],
    "apple": ["apple"],
    "netflix": ["netflix"],
    "flipkart": ["flipkart"],
    "adobe": ["adobe"],
    "accenture": ["accenture"],
}

# Difficulty alias map
DIFFICULTY_MAP = {
    "beginner": "Easy",
    "easy": "Easy",
    "intermediate": "Medium",
    "medium": "Medium",
    "advanced": "Hard",
    "hard": "Hard",
}

class PineconeRAGClient:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.pinecone_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_env = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "placement-questions")
        
        self.embeddings = None
        self.pc = None
        self.is_active = False

        if HAS_GOOGLE_EMB and self.gemini_key:
            try:
                _emb_model = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
                self.embeddings = GoogleGenerativeAIEmbeddings(
                    model=_emb_model,
                    google_api_key=self.gemini_key
                )
                if HAS_PINECONE and self.pinecone_key:
                    self.pc = Pinecone(api_key=self.pinecone_key)
                    self._initialize_index()
                    self.is_active = True
                    logger.info("Pinecone client with Gemini Embeddings active.")
            except Exception as e:
                logger.warning(f"Embeddings/Pinecone init failed, using local DB: {e}")
        
        if not self.is_active:
            logger.info(f"RAG using local knowledge base with {len(KNOWLEDGE_SEED)} questions.")

    def _initialize_index(self):
        try:
            indexes = [idx.name for idx in self.pc.list_indexes()]
            if self.index_name not in indexes:
                logger.info(f"Creating Pinecone Index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=768,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region=self.pinecone_env)
                )
                self._seed_index()
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone index: {e}")

    def _seed_index(self):
        if not self.embeddings:
            return
        try:
            index = self.pc.Index(self.index_name)
            vectors = []
            for item in KNOWLEDGE_SEED:
                text_to_embed = f"Question: {item['question']}\nTopic: {item['topic']}\nAnswer: {item['expected_answer']}"
                embedding = self.embeddings.embed_query(text_to_embed)
                vectors.append({
                    "id": item["id"],
                    "values": embedding,
                    "metadata": {
                        "question": item["question"],
                        "expected_answer": item["expected_answer"],
                        "topic": item["topic"],
                        "difficulty": item["difficulty"],
                        "company": item["company"],
                        "type": item["type"]
                    }
                })
            index.upsert(vectors=vectors)
            logger.info("Pinecone database successfully seeded with Gemini embeddings.")
        except Exception as e:
            logger.error(f"Seeding index failed: {e}")

    def _normalize_difficulty(self, difficulty: str) -> str:
        """Normalize difficulty strings like 'advanced' → 'Hard'"""
        if not difficulty:
            return None
        return DIFFICULTY_MAP.get(difficulty.lower().strip(), difficulty.capitalize())

    def _companies_match(self, question_company: str, target_companies: List[str]) -> bool:
        """Check if any target company appears in question's company list (case-insensitive)"""
        if not target_companies or not question_company:
            return True
        
        q_lower = question_company.lower()
        
        for target in target_companies:
            t_lower = target.lower().strip()
            # Direct substring match
            if t_lower in q_lower:
                return True
            
            # Alias match
            for canonical, aliases in COMPANY_ALIASES.items():
                if any(alias in t_lower for alias in aliases):
                    if any(alias in q_lower for alias in aliases):
                        return True
        
        return False

    def query_questions(self,
                        query_text: str,
                        companies: Optional[List[str]] = None,
                        difficulty: Optional[str] = None,
                        topic: Optional[str] = None,
                        limit: int = 5,
                        weak_areas: List[str] = None) -> List[Dict[str, Any]]:
        """
        Queries questions using semantic search (Pinecone) or local fallback.
        Filters by company, difficulty, and topic with fuzzy matching.
        """
        weak_areas = weak_areas or []
        
        # Normalize difficulty
        norm_difficulty = self._normalize_difficulty(difficulty)
        
        logger.info(f"RAG Query: companies={companies}, difficulty={difficulty}→{norm_difficulty}, topic={topic}")

        # 1. Try Pinecone vector search
        if self.is_active and self.pc:
            try:
                index = self.pc.Index(self.index_name)
                vector = self.embeddings.embed_query(query_text)
                
                filters = {}
                if norm_difficulty:
                    filters["difficulty"] = norm_difficulty
                if topic:
                    filters["topic"] = topic
                    
                query_params = {
                    "vector": vector,
                    "top_k": limit * 3,
                    "include_metadata": True
                }
                if filters:
                    query_params["filter"] = filters
                    
                matches = index.query(**query_params).matches
                results = []
                for match in matches:
                    meta = match.metadata
                    results.append({
                        "id": match.id,
                        "question": meta.get("question"),
                        "expected_answer": meta.get("expected_answer"),
                        "topic": meta.get("topic"),
                        "difficulty": meta.get("difficulty"),
                        "company": meta.get("company"),
                        "type": meta.get("type"),
                        "score": match.score
                    })
                
                logger.info(f"[PINECONE RAG] Questions returned from Pinecone query BEFORE company filtering: {[r['id'] for r in results]}")
                # Apply company filter post-retrieval (since metadata filter is exact)
                if companies:
                    results = [r for r in results if self._companies_match(r.get("company", ""), companies)]
                logger.info(f"[PINECONE RAG] Questions returned from Pinecone query AFTER company filtering: {[r['id'] for r in results]}")
                
                if results:
                    return self._apply_rerank(results, weak_areas, companies)[:limit]
            except Exception as e:
                logger.warning(f"Pinecone search failed, using local DB: {e}")

        # 2. Local Knowledge Base Fallback (always works)
        raw_candidates = []
        for item in KNOWLEDGE_SEED:
            # Difficulty filter (normalized)
            if norm_difficulty and item["difficulty"].lower() != norm_difficulty.lower():
                continue
            # Topic filter
            if topic and topic.lower() not in item["topic"].lower():
                continue
            raw_candidates.append(item)

        logger.info(f"[LOCAL RAG] Candidates matching difficulty/topic BEFORE company filtering: {[c['id'] for c in raw_candidates]}")

        results = []
        for item in raw_candidates:
            # Company filter (fuzzy)
            if companies and not self._companies_match(item["company"], companies):
                continue
                
            # Relevance scoring
            score = 0.0
            query_words = query_text.lower().split()
            for word in query_words:
                if len(word) > 3:
                    if word in item["question"].lower():
                        score += 2.0
                    if word in item["topic"].lower():
                        score += 1.5
            
            results.append({**item, "score": score})
            
        results.sort(key=lambda x: x["score"], reverse=True)
        final = self._apply_rerank(results, weak_areas, companies)
        
        logger.info(f"Local RAG returned {len(final)} questions (companies={companies}, difficulty={norm_difficulty})")
        return final[:limit]

    def _apply_rerank(self, questions: List[Dict[str, Any]], weak_areas: List[str], target_companies: Optional[List[str]]) -> List[Dict[str, Any]]:
        """Boost scores for weak-area topics and target company matches."""
        weaks_lower = [w.lower().strip() for w in weak_areas]
        for q in questions:
            boost = 0.0
            if q["topic"].lower().strip() in weaks_lower:
                boost += 0.5
            if target_companies and self._companies_match(q.get("company", ""), target_companies):
                boost += 1.0
            q["score"] = q.get("score", 1.0) + boost
            
        questions.sort(key=lambda x: x["score"], reverse=True)
        return questions

pinecone_rag = PineconeRAGClient()
