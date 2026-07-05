// Client state parameters
let userId = null;
let userName = null;
let currentQuestion = null;
let currentQuestions = [];
let currentQuestionIndex = 0;
let answeredQuestionsCount = 0;
let selectedSubject = "Coding";
let prepLevel = "advanced";
let chatHistory = [];
let isMockMode = false;
const apiEndpoint = "http://localhost:8000";

// DOM Elements
const authOverlay = document.getElementById("auth-overlay");
const navbar = document.getElementById("navbar");
const dashboardSelection = document.getElementById("dashboard-selection");
const agentSection = document.getElementById("agent-section");
const userGreeting = document.getElementById("user-greeting");
const activeSubjectTitle = document.getElementById("active-subject-title");

// Workspace Solver Elements
const prepConfigForm = document.getElementById("prep-config-form");
const activeSolverWorkspace = document.getElementById("active-solver-workspace");
const problemStatement = document.getElementById("problem-statement");
const problemDifficulty = document.getElementById("problem-difficulty");
const problemTopic = document.getElementById("problem-topic");
const problemCompany = document.getElementById("problem-company");

const solverInput = document.getElementById("solver-input");
const referenceSection = document.getElementById("reference-section");
const referenceBody = document.getElementById("reference-body");

const feedbackSection = document.getElementById("feedback-section");
const feedbackScore = document.getElementById("feedback-score");
const feedbackBody = document.getElementById("feedback-body");

const roadmapsSection = document.getElementById("roadmaps-section");
const roadmapLinks = document.getElementById("roadmap-links");

const loadingOverlay = document.getElementById("loading-overlay");
const loadingText = document.getElementById("loading-text");
const toast = document.getElementById("toast");

// Initialize application
window.addEventListener("DOMContentLoaded", () => {
  if (prepConfigForm) {
      originalPrepConfigHTML = prepConfigForm.innerHTML;
  }
  const savedUserId = localStorage.getItem("placement_user_id");
  const savedName = localStorage.getItem("placement_user_name");
  const savedToken = localStorage.getItem("placement_user_token");

  if (savedUserId && savedName && savedToken) {
    userId = savedUserId;
    userName = savedName;
    showDashboard(true);
  } else {
    localStorage.clear();
    showDashboard(false);
  }
  
  checkApiServerConnection();
});

// Check server connection
async function checkApiServerConnection() {
  try {
    const res = await fetch(`${apiEndpoint}/`, { signal: AbortSignal.timeout(1500) });
    if (res.ok) {
      isMockMode = false;
      showToast("Connected to live Gemini backend!", "success");
    } else {
      throw new Error();
    }
  } catch (err) {
    isMockMode = true;
    showToast("Running in offline Mock Mode (Local Simulator)", "info");
  }
}

// Helper for Bearer token headers
function getAuthHeaders() {
  const token = localStorage.getItem("placement_user_token");
  return {
    "Content-Type": "application/json",
    "Authorization": token ? `Bearer ${token}` : ""
  };
}

// Alert Toast
function showToast(message, type = "info") {
  toast.innerText = message;
  toast.className = `toast show ${type}`;
  setTimeout(() => {
    toast.className = "toast";
  }, 4000);
}

// SignUp click handler
async function handleSignUp() {
  const name = document.getElementById("auth-name") ? document.getElementById("auth-name").value.trim() : "";
  const email = document.getElementById("auth-email").value.trim();
  const password = document.getElementById("auth-password").value;

  if (!email || !password) {
    showToast("Email and Password are required!", "danger");
    return;
  }

  showLoading("Authenticating...");
  try {
    const res = await fetch(`${apiEndpoint}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: email,
        password: password,
        name: name || undefined
      })
    });
    
    const data = await res.json();
    showLoading(false);
    
    if (res.ok && data.success !== false) {
      userId = email;
      userName = data.name || name || "Student";
      localStorage.setItem("placement_user_id", userId);
      localStorage.setItem("placement_user_name", userName);
      localStorage.setItem("placement_user_token", data.token); // Save JWT Token
      
      // Default values setup (safely check if element exists)
      const resumeInput = document.getElementById("student-resume");
      if (resumeInput) resumeInput.value = `Student Profile:\nName: ${userName}\nEmail: ${email}`;

      showToast(`Logged in successfully! Welcome ${userName}.`, "success");
      showDashboard(true);
    } else {
      showToast(data.message || data.detail || "Authentication failed.", "danger");
    }
  } catch (e) {
    showLoading(false);
    console.error("Auth error:", e);
    showToast("Server communication error. Check if backend is running.", "danger");
  }
}

// Mock Google Sign-In
async function handleGoogleSignIn() {
  const googleEmail = prompt("Simulating Google Sign-In...\nPlease enter your Google Account Email:", "");
  if (!googleEmail) return; // User cancelled
  if (!googleEmail.includes("@")) {
    showToast("Invalid email format.", "danger");
    return;
  }

  showLoading("Authenticating with Google...");
  try {
    const res = await fetch(`${apiEndpoint}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: googleEmail,
        password: "google_oauth_placeholder",
        name: googleEmail.split("@")[0],
        is_google: true
      })
    });
    
    const data = await res.json();
    showLoading(false);

    if (res.ok && data.success !== false) {
      userId = data.email || googleEmail;
      userName = data.name || googleEmail.split("@")[0];
      localStorage.setItem("placement_user_id", userId);
      localStorage.setItem("placement_user_name", userName);
      localStorage.setItem("placement_user_token", data.token); // Save JWT Token
      localStorage.setItem("placement_auth_provider", "google");
      
      const resumeInput = document.getElementById("student-resume");
      if (resumeInput) resumeInput.value = `Google Profile:\nName: ${userName}\nEmail: ${userId}`;

      showToast(`Signed in with Google as ${userName}.`, "success");
      showDashboard(true);
    } else {
      showToast(data.message || data.detail || "Google Auth failed.", "danger");
    }
  } catch (e) {
    showLoading(false);
    console.error("Google Auth error:", e);
    showToast("Server error during Google Login.", "danger");
  }
}

// Logout handler
function handleLogout() {
  localStorage.clear();
  userId = null;
  userName = null;
  showDashboard(false);
  showToast("Logged out successfully");
}

// Toggle dashboards
function showDashboard(isLoggedIn) {
  if (isLoggedIn) {
    authOverlay.style.display = "none";
    navbar.style.display = "block";
    dashboardSelection.style.display = "block";
    agentSection.style.display = "none";
    userGreeting.innerText = `Welcome, ${userName}`;
  } else {
    authOverlay.style.display = "flex";
    navbar.style.display = "none";
    dashboardSelection.style.display = "none";
    agentSection.style.display = "none";
  }
}

// Dynamic Topics Database
const companyTopicsDB = {
  "Coding": {
    "Google": "Graphs, Dynamic Programming, Trees, Hard Arrays",
    "Amazon": "Trees, Linked Lists, System Design, Sliding Window",
    "Microsoft": "Arrays, Strings, Trees, Linked Lists",
    "TCS": "Basic Arrays, Strings, Pattern Printing",
    "Infosys": "Strings, Matrices, Mathematics",
    "Cognizant": "String Manipulation, Sorting, Basic Data Structures",
    "Wipro": "Arrays, Mathematical, Pattern Logic"
  },
  "Aptitude": {
    "Google": "Probability, Permutation & Combination, Puzzles",
    "Amazon": "Time & Work, Profit & Loss, Ratios",
    "Microsoft": "Logical Reasoning, Data Sufficiency",
    "TCS": "Percentages, Time & Speed, Blood Relations",
    "Infosys": "Syllogism, Cryptarithmetic, Data Interpretation",
    "Cognizant": "Number System, Profit & Loss, Seating Arrangement",
    "Wipro": "Time & Work, Coding Decoding, Number Series"
  },
  "System Design": {
    "Google": "Distributed Systems, Rate Limiting, High Availability",
    "Amazon": "E-commerce scaling, Microservices, Storage Systems",
    "Microsoft": "Cloud Architecture, SQL vs NoSQL, Load Balancing",
    "TCS": "Basic Client-Server Architecture, Database Normalization",
    "Infosys": "API Design, Caching",
    "Cognizant": "Web Application Architecture, Database Indexes",
    "Wipro": "Load Balancers, Basic API Design"
  },
  "Behavioral": {
    "Google": "Leadership, Googleyness, Conflict Resolution",
    "Amazon": "Amazon Leadership Principles, Bias for Action",
    "Microsoft": "Teamwork, Problem Solving, Empathy",
    "TCS": "Adaptability, Relocation, Team Management",
    "Infosys": "Client Handling, Time Management",
    "Cognizant": "Flexibility, Working under pressure",
    "Wipro": "Team collaboration, Ethics"
  }
};

document.addEventListener('change', (e) => {
  if (e.target && e.target.closest('#company-checkboxes') && e.target.type === 'checkbox') {
    updateDynamicTopics();
  }
});

function updateDynamicTopics() {
  const container = document.getElementById('aptitude-topics-group');
  const list = document.getElementById('dynamic-topics-list');
  
  if (selectedSubject !== "Aptitude") {
    if (container) container.style.display = "none";
    return;
  }

  const checked = Array.from(document.querySelectorAll('#company-checkboxes input[type="checkbox"]:checked')).map(cb => cb.value);
  
  if (checked.length === 0) {
    if (list) list.innerHTML = "Select a company to see topics.";
    return;
  }
  
  let html = '<ul style="margin:0; padding-left:1rem;">';
  checked.forEach(comp => {
    let topics = "Standard placement topics";
    if (companyTopicsDB["Aptitude"] && companyTopicsDB["Aptitude"][comp]) {
      topics = companyTopicsDB["Aptitude"][comp];
    }
    html += `<li style="margin-bottom:4px;"><strong>${comp}:</strong> ${topics}</li>`;
  });
  html += '</ul>';
  
  if (list) list.innerHTML = html;
  if (container) container.style.display = "block";
}

// Backup original settings form HTML to allow resetting the workspace later
let originalPrepConfigHTML = "";

// Select Subject Card
function selectSubject(subject) {
  selectedSubject = subject;
  activeSubjectTitle.innerText = subject;
  
  // Restore original form content if it was overwritten by the summary panel
  if (originalPrepConfigHTML && prepConfigForm) {
      prepConfigForm.innerHTML = originalPrepConfigHTML;
  }
  
  dashboardSelection.style.display = "none";
  agentSection.style.display = "block";
  
  // Toggle form groups based on subject
  const codingLang = document.getElementById("coding-language-group");
  const codingResume = document.getElementById("coding-resume-group");
  const aptTopics = document.getElementById("aptitude-topics-group");
  const behavUpload = document.getElementById("behavioral-upload-group");
  const prepDiff = document.getElementById("prep-difficulty-group");
  
  if (codingLang) codingLang.style.display = subject === "Coding" ? "block" : "none";
  if (codingResume) codingResume.style.display = subject === "Coding" ? "block" : "none";
  if (aptTopics) aptTopics.style.display = subject === "Aptitude" ? "block" : "none";
  if (behavUpload) behavUpload.style.display = subject === "Behavioral" ? "block" : "none";
  if (prepDiff) prepDiff.style.display = subject === "Coding" ? "block" : "none";

  // Show settings, hide solver
  prepConfigForm.style.display = "block";
  activeSolverWorkspace.style.display = "none";
  referenceSection.style.display = "none";
  document.getElementById("btn-finish-summary").style.display = "none";
  document.getElementById("pagination-controls").style.display = "none";
  
  // Reset outputs
  problemStatement.innerText = "Select parameters and click 'Start Practice' to pull the first question.";
  updateDynamicTopics();
}

function goBackToDashboard() {
  dashboardSelection.style.display = "block";
  agentSection.style.display = "none";
  currentQuestion = null;
}

// Choose prep level
function selectPrep(level) {
  prepLevel = level;
  document.querySelectorAll(".prep-btn").forEach(btn => btn.classList.remove("active"));
  document.getElementById(`prep-${level}`).classList.add("active");
}

// Initialize interview session
async function startInterview() {
  const skillsElement = document.getElementById("student-skills");
  const skills = skillsElement ? skillsElement.value.trim() : "";
  const checkedComps = Array.from(document.querySelectorAll('#company-checkboxes input[type="checkbox"]:checked')).map(cb => cb.value);
  const goal = checkedComps.join(", ");
  const weakElement = document.getElementById("student-weak");
  const weak = weakElement ? weakElement.value.trim() : "";
  const resume = document.getElementById("student-resume").value.trim();

  if (checkedComps.length === 0) {
    showToast("Please select at least one Target Company!", "warning");
    return;
  }
  
  answeredQuestionsCount = 0;
  document.getElementById("btn-finish-summary").style.display = "none";

  // Handle Behavioral Resume Upload
  let finalResumeText = resume;
  if (selectedSubject === "Behavioral") {
    const uploadInput = document.getElementById("resume-upload");
    if (uploadInput && uploadInput.files.length > 0) {
       document.getElementById("ats-analysis-loading").style.display = "block";
       showLoading("Uploading and analyzing resume for ATS check...");
       try {
           const formData = new FormData();
           formData.append("file", uploadInput.files[0]);
           
           const token = localStorage.getItem("placement_user_token");
           const uploadRes = await fetch(`${apiEndpoint}/resume/upload`, {
               method: "POST",
               headers: {
                   "Authorization": token ? `Bearer ${token}` : ""
               },
               body: formData
           });
           
           if (!uploadRes.ok) throw new Error("Failed to upload resume.");
           const uploadData = await uploadRes.json();
           finalResumeText = uploadData.extracted_text;
           document.getElementById("ats-analysis-loading").style.display = "none";
           
           if (uploadData.ats_analysis) {
               document.getElementById("resume-rating-box").style.display = "block";
               document.getElementById("resume-rating-score").innerText = `${uploadData.ats_analysis.ats_score} / 100`;
               document.getElementById("resume-rating-label").innerText = "ATS Compatibility";
               document.getElementById("resume-rating-feedback").innerHTML = `
                   <strong>Strengths:</strong> ${uploadData.ats_analysis.best_points.join(", ")}<br>
                   <strong>To Improve:</strong> ${uploadData.ats_analysis.improvement_areas.join(", ")}
               `;
           }
       } catch (e) {
           showLoading(false);
           document.getElementById("ats-analysis-loading").style.display = "none";
           showToast(`Error: ${e.message}`, "danger");
           return;
       }
    } else {
       showToast("Please upload a resume for Behavioral assessment.", "warning");
       return;
    }
  }

  showLoading(`🚀 Starting session for ${selectedSubject} — Company: ${goal}...`);
  
  const payload = {
    skills: skills,
    subject: selectedSubject,
    companies: checkedComps,
    weak_areas: weak || selectedSubject,
    resume_text: finalResumeText,
    difficulty: prepLevel
  };

  try {
    const res = await fetch(`${apiEndpoint}/assessment/start`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      showLoading(false);
      prepConfigForm.style.display = "none";
      activeSolverWorkspace.style.display = "block";
      showToast("Session synced! Generating your curriculum...", "success");
      
      // Clear previous rating unless it's Behavioral (already set by upload)
      if (selectedSubject !== "Behavioral") {
          document.getElementById("resume-rating-box").style.display = "none";
      }
      
      if (selectedSubject === "Coding") {
          triggerNextQuestion();
      } else if (selectedSubject === "Behavioral" && finalResumeText) {
          // Already have ATS rating, just trigger next question
          triggerNextQuestion();
      } else if (finalResumeText) {
          waitForResumeRating();
      } else {
          triggerNextQuestion();
      }
    } else {
      throw new Error(`Server returned ${res.status}`);
    }
  } catch (e) {
    showLoading(false);
    showToast(`Error: ${e.message}. Check backend terminal.`, "danger");
  }
}

async function waitForResumeRating() {
    showLoading("🤖 Agent is analyzing and rating your resume...");
    let attempts = 0;
    
    const poll = async () => {
        try {
            const res = await fetch(`${apiEndpoint}/assessment/status`, {
                headers: getAuthHeaders()
            });
            const data = await res.json();
            
            if (data.resume_rating) {
                document.getElementById("resume-rating-box").style.display = "block";
                document.getElementById("resume-rating-score").innerText = data.resume_rating;
                document.getElementById("resume-rating-label").innerText = data.resume_rating_label;
                document.getElementById("resume-rating-feedback").innerText = data.resume_feedback;
                
                showLoading(false);
                showToast("Resume analysis complete!", "success");
                triggerNextQuestion();
            } else if (attempts < 10) {
                attempts++;
                setTimeout(poll, 3000);
            } else {
                // Timeout after 30s
                showLoading(false);
                triggerNextQuestion();
            }
        } catch (e) {
            showLoading(false);
            triggerNextQuestion();
        }
    };
    
    setTimeout(poll, 2000);
}

// Fetch Next Question(s)
async function triggerNextQuestion() {
  showLoading("🔍 Querying database for your questions...");
  feedbackSection.style.display = "none";
  referenceSection.style.display = "none";
  solverInput.value = "";
  
  try {
    let endpoint = `${apiEndpoint}/question/next`;
    if (selectedSubject === "Coding") {
      endpoint = `${apiEndpoint}/question/batch`;
    }

    const res = await fetch(endpoint, {
        headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    const data = await res.json();
    showLoading(false);
    
    if (selectedSubject === "Coding" && Array.isArray(data)) {
        currentQuestions = data;
        currentQuestionIndex = 0;
        document.getElementById("pagination-controls").style.display = "flex";
        updatePaginationUI();
        currentQuestion = currentQuestions[currentQuestionIndex];
    } else {
        document.getElementById("pagination-controls").style.display = "none";
        currentQuestion = data;
    }
    
    renderQuestion(currentQuestion);
    showToast("Question loaded! Write your answer and submit.", "success");
  } catch (e) {
    showLoading(false);
    showToast(`Failed to fetch question: ${e.message}`, "danger");
    console.error("triggerNextQuestion error:", e);
  }
}

function prevQuestion() {
    if (currentQuestionIndex > 0) {
        currentQuestionIndex--;
        currentQuestion = currentQuestions[currentQuestionIndex];
        updatePaginationUI();
        renderQuestion(currentQuestion);
        resetWorkspaceForNewQuestion();
    }
}

function nextQuestion() {
    if (currentQuestionIndex < currentQuestions.length - 1) {
        currentQuestionIndex++;
        currentQuestion = currentQuestions[currentQuestionIndex];
        updatePaginationUI();
        renderQuestion(currentQuestion);
        resetWorkspaceForNewQuestion();
    }
}

function updatePaginationUI() {
    document.getElementById("pagination-text").innerText = `${currentQuestionIndex + 1} of ${currentQuestions.length}`;
}

function resetWorkspaceForNewQuestion() {
    feedbackSection.style.display = "none";
    referenceSection.style.display = "none";
    solverInput.value = "";
}

// Render problem statement details
function renderQuestion(q) {
  problemStatement.innerText = q.question;
  problemDifficulty.innerText = q.difficulty;
  problemTopic.innerText = `Topic: ${q.topic}`;
  problemCompany.innerText = `Target: ${q.company || "All Companies"}`;
  
  const aiBadge = document.getElementById("ai-generated-badge");
  if (aiBadge) {
      aiBadge.style.display = q.is_ai_generated ? "inline-block" : "none";
  }
  
  // Format difficulty badge color
  if (q.difficulty.toLowerCase() === "easy") {
    problemDifficulty.style.color = "var(--success)";
    problemDifficulty.style.borderColor = "var(--success)";
    problemDifficulty.style.background = "rgba(16, 185, 129, 0.08)";
  } else if (q.difficulty.toLowerCase() === "medium") {
    problemDifficulty.style.color = "var(--warning)";
    problemDifficulty.style.borderColor = "var(--warning)";
    problemDifficulty.style.background = "rgba(245, 158, 11, 0.08)";
  } else {
    problemDifficulty.style.color = "var(--danger)";
    problemDifficulty.style.borderColor = "var(--danger)";
    problemDifficulty.style.background = "rgba(239, 68, 68, 0.08)";
  }
}

// Submit answer button click
async function submitSolverAnswer() {
  const ans = solverInput.value.trim();
  if (!ans) {
    showToast("Please write your answer implementation first!", "warning");
    return;
  }

  showLoading("⚡ Evaluating your answer...");

  try {
    const res = await fetch(`${apiEndpoint}/answer/submit`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ answer: ans, question: currentQuestion })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    showLoading(false);
    
    answeredQuestionsCount++;
    if (answeredQuestionsCount >= 1) {
        document.getElementById("btn-finish-summary").style.display = "inline-block";
    }

    feedbackSection.style.display = "block";
    feedbackScore.innerText = Math.round(data.evaluation.score);
    feedbackBody.innerHTML = `<strong>AI Trainer Feedback:</strong><br/>${data.evaluation.feedback}`;
    
    referenceSection.style.display = "block";
    referenceBody.innerHTML = `<strong>✅ Optimal Solution Approach:</strong><br/><pre><code>${currentQuestion.expected_answer}</code></pre>`;
    
    chatHistory.push({ q: currentQuestion.id, score: data.evaluation.score });
    
    const scoreVal = Math.round(data.evaluation.score);
    if (scoreVal >= 70) {
      showToast(`Great answer! Score: ${scoreVal}/100.`, "success");
    } else {
      showToast(`Score: ${scoreVal}/100. Review the solution above to improve!`, "info");
    }
    
    setTimeout(() => {
      if (selectedSubject !== "Coding") {
         if (data.next_step === "complete") {
           showFinalPerformanceSummary();
         } else {
           triggerNextQuestion();
         }
      }
    }, 6000);
  } catch (e) {
    showLoading(false);
    showToast(`Error submitting answer: ${e.message}`, "danger");
    console.error("submitSolverAnswer error:", e);
  }
}

// Render final results
async function showFinalPerformanceSummary() {
  showTyping(true);
  
  try {
    const res = await fetch(`${apiEndpoint}/progress`, {
        headers: getAuthHeaders()
    });
    const data = await res.json();
    showTyping(false);
    
    activeSolverWorkspace.style.display = "none";
    prepConfigForm.style.display = "block";
    
    let recsList = "";
    data.recommendations.forEach(r => {
      recsList += `<div class="roadmap-item">
        <strong>${r.topic}</strong>
        ${r.links.map(l => `<a href="${l.url}" target="_blank">${l.name} (${l.type})</a>`).join(" | ")}
      </div>`;
    });
    
    prepConfigForm.innerHTML = `
      <div class="feedback-body" style="background:#f8fafc; border-color:var(--border-color)">
        <h3 style="color:var(--color-primary); margin-bottom:1rem">🎉 Placement Assessment Summary</h3>
        <p><strong>Readiness Score:</strong> ${data.readiness_score}/100</p>
        <p><strong>Placement Success Probability:</strong> ${data.placement_probability}%</p>
        <p style="margin-top:1rem"><strong>Weak Areas Identifed:</strong> ${data.weak_areas.join(", ") || "None flagged!"}</p>
        
        <div style="margin-top:1.5rem">
          <h5>📚 Recommended Roadmaps:</h5>
          <div class="roadmap-links" style="margin-top:0.5rem">
            ${recsList || "<p>All areas mastered! Keep it up.</p>"}
          </div>
        </div>
        <button onclick="selectSubject('${selectedSubject}')" class="btn-workspace-start" style="margin-top:1.5rem">Practice Again</button>
      </div>
    `;
    currentQuestion = null;
  } catch (e) {
    showTyping(false);
    showToast("Error compiling final results.", "danger");
  }
}

// Show/hide loading overlay
function showLoading(messageOrFalse) {
  if (messageOrFalse === false || messageOrFalse === undefined) {
    loadingOverlay.style.display = "none";
  } else {
    loadingText.innerText = messageOrFalse;
    loadingOverlay.style.display = "flex";
  }
}

function showTyping(show) {
  // legacy compat – use showLoading instead
}
