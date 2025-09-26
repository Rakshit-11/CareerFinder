import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Separator } from './components/ui/separator';
import { toast } from 'sonner';
import { Toaster } from './components/ui/sonner';
import { 
  User, 
  Trophy, 
  Download, 
  Send, 
  Clock, 
  Star,
  BookOpen,
  Target,
  CheckCircle,
  ArrowRight,
  Brain,
  BarChart3,
  Zap,
  Flame,
  Shield,
  Rocket,
  AlertTriangle,
  Timer
} from 'lucide-react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

//

// Simple metadata for known badges; unknown badges get sensible defaults
const BADGE_META = {
  'Debugging Specialist': {
    icon: '🛠️',
    color: 'from-rose-50 to-orange-50',
    description: 'Identified all critical bugs in the codebase',
    rarity: 'Common',
    rarityPct: '12.4%'
  },
  'API Development Expert': {
    icon: '🔗',
    color: 'from-blue-50 to-cyan-50',
    description: 'Built a secure authentication API',
    rarity: 'Common',
    rarityPct: '10.8%'
  },
  'Quality Assurance Professional': {
    icon: '🧪',
    color: 'from-indigo-50 to-violet-50',
    description: 'Wrote comprehensive unit tests',
    rarity: 'Common',
    rarityPct: '9.6%'
  },
  'Cloud Architect': {
    icon: '☁️',
    color: 'from-sky-50 to-blue-50',
    description: 'Designed a scalable cloud architecture',
    rarity: 'Rare',
    rarityPct: '5.1%'
  },
  'Monitoring Strategist': {
    icon: '📈',
    color: 'from-emerald-50 to-green-50',
    description: 'Implemented effective monitoring and alerts',
    rarity: 'Common',
    rarityPct: '8.3%'
  },
};

 

// Auth Context
const AuthContext = React.createContext();

const useAuth = () => {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      const { access_token } = response.data;
      setToken(access_token);
      localStorage.setItem('token', access_token);
      await fetchUser(access_token);
      return true;
    } catch (error) {
      toast.error('Login failed: ' + (error.response?.data?.detail || 'Unknown error'));
      return false;
    }
  };

  const register = async (email, username, password) => {
    try {
      const response = await axios.post(`${API}/auth/register`, { email, username, password });
      const { access_token } = response.data;
      setToken(access_token);
      localStorage.setItem('token', access_token);
      await fetchUser(access_token);
      return true;
    } catch (error) {
      toast.error('Registration failed: ' + (error.response?.data?.detail || 'Unknown error'));
      return false;
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
  };

  const fetchUser = async (accessToken = token) => {
    if (!accessToken) {
      setLoading(false);
      return;
    }

    try {
      const response = await axios.get(`${API}/auth/me`, {
        headers: { Authorization: `Bearer ${accessToken}` }
      });
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, loading, fetchUser }}>
      {children}
    </AuthContext.Provider>
  );
};

// Landing Page Component
const LandingPage = () => {
  const { login, register } = useAuth();
  const [isLoginMode, setIsLoginMode] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    let success;
    if (isLoginMode) {
      success = await login(formData.email, formData.password);
    } else {
      success = await register(formData.email, formData.username, formData.password);
    }
    
    if (success) {
      toast.success(isLoginMode ? 'Welcome back!' : 'Account created successfully!');
    }
  };

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-orange-50 to-white">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-md sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <Target className="h-8 w-8 text-orange-600" />
            <h1 className="text-2xl font-bold text-gray-900">Project Pathfinder</h1>
          </div>
          <p className="text-sm text-gray-600 hidden md:block">Learn by Trying, Not Guessing</p>
        </div>
      </header>

      <div className="container mx-auto px-4 py-12">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Hero Content */}
          <div className="space-y-8">
            <div className="space-y-4">
              <Badge className="bg-orange-100 text-orange-700 border-orange-200">
                Career Discovery Platform
              </Badge>
              <h2 className="text-5xl font-bold text-gray-900 leading-tight">
                Discover tech careers by 
                <span className="text-orange-600 block">actually doing the work</span>
              </h2>
              <p className="text-xl text-gray-600 leading-relaxed">
                Skip the confusing personality quizzes. Complete hands-on tech simulations that mirror real jobs and get instant AI feedback to discover what truly excites you.
              </p>
            </div>

            {/* Features Grid */}
            <div className="grid md:grid-cols-2 gap-4">
              <div className="flex items-start space-x-3 p-4 rounded-xl bg-white border">
                <Brain className="h-6 w-6 text-orange-600 mt-1" />
                <div>
                  <h4 className="font-semibold text-gray-900">AI-Powered Feedback</h4>
                  <p className="text-sm text-gray-600">Get intelligent insights on your work, just like a real mentor</p>
                </div>
              </div>
              <div className="flex items-start space-x-3 p-4 rounded-xl bg-white border">
                <BarChart3 className="h-6 w-6 text-orange-600 mt-1" />
                <div>
                  <h4 className="font-semibold text-gray-900">Real Tech Tasks</h4>
                  <p className="text-sm text-gray-600">Work with actual code, data, and industry tools</p>
                </div>
              </div>
              <div className="flex items-start space-x-3 p-4 rounded-xl bg-white border">
                <Trophy className="h-6 w-6 text-orange-600 mt-1" />
                <div>
                  <h4 className="font-semibold text-gray-900">Skill Badges</h4>
                  <p className="text-sm text-gray-600">Earn recognition for completing career simulations</p>
                </div>
              </div>
              <div className="flex items-start space-x-3 p-4 rounded-xl bg-white border">
                <Clock className="h-6 w-6 text-orange-600 mt-1" />
                <div>
                  <h4 className="font-semibold text-gray-900">Quick & Focused</h4>
                  <p className="text-sm text-gray-600">Most tasks take 15-30 minutes to complete</p>
                </div>
              </div>
            </div>
          </div>

          {/* Auth Form */}
          <div className="bg-white rounded-2xl shadow-xl p-8 border">
            <div className="text-center mb-8">
              <h3 className="text-2xl font-bold text-gray-900 mb-2">
                {isLoginMode ? 'Welcome Back' : 'Start Exploring'}
              </h3>
              <p className="text-gray-600">
                {isLoginMode ? 'Continue your career discovery journey' : 'Create your account to begin'}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-4">
                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    placeholder="your@email.com"
                    required
                    className="mt-1"
                  />
                </div>

                {!isLoginMode && (
                  <div>
                    <Label htmlFor="username">Username</Label>
                    <Input
                      id="username"
                      name="username"
                      value={formData.username}
                      onChange={handleInputChange}
                      placeholder="Your username"
                      required
                      className="mt-1"
                    />
                  </div>
                )}

                <div>
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    name="password"
                    type="password"
                    value={formData.password}
                    onChange={handleInputChange}
                    placeholder="••••••••"
                    required
                    className="mt-1"
                  />
                </div>
              </div>

              <Button type="submit" className="w-full bg-orange-600 hover:bg-orange-700 text-white">
                {isLoginMode ? 'Sign In' : 'Create Account'}
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </form>

            <div className="mt-6 text-center">
              <button
                onClick={() => setIsLoginMode(!isLoginMode)}
                className="text-orange-600 hover:text-orange-700 font-medium"
              >
                {isLoginMode 
                  ? "Don't have an account? Sign up" 
                  : 'Already have an account? Sign in'
                }
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Dashboard Component
const Dashboard = () => {
  const { user, logout, fetchUser } = useAuth();
  const [techFields, setTechFields] = useState([]);
  const [selectedField, setSelectedField] = useState(null);
  const [simulations, setSimulations] = useState([]);
  const [selectedSimulation, setSelectedSimulation] = useState(null);
  const [userAnswer, setUserAnswer] = useState('');
  const [submission, setSubmission] = useState(null);
  const [loading, setLoading] = useState(false);
  // Engagement states
  const [revealedHints, setRevealedHints] = useState(0);
  const [checklistState, setChecklistState] = useState([]);
  const [startTime, setStartTime] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const [attempts, setAttempts] = useState(0);
  const [questionAnswers, setQuestionAnswers] = useState({});
  const [questionHintsRevealed, setQuestionHintsRevealed] = useState({});
  const [questionResults, setQuestionResults] = useState({});
  const [streakCount, setStreakCount] = useState(0);
  const [showAchievement, setShowAchievement] = useState(null);
  const [totalScore, setTotalScore] = useState(0);

  useEffect(() => {
    initializeData();
  }, []);

  const initializeData = async () => {
    try {
      await initializeTechFields();
      await initializeSimulations();
      // Merge questions into existing simulations (idempotent)
      try {
        await axios.post(`${API}/admin/merge-simulation-questions`);
      } catch (e) {
        // non-fatal in dev
        console.warn('Question merge skipped:', e?.response?.data || e?.message);
      }
      await fetchTechFields();
      await fetchAllSimulations();
    } catch (error) {
      console.error('Failed to initialize data:', error);
    }
  };

  const fetchAllSimulations = async () => {
    try {
      const response = await axios.get(`${API}/simulations`);
      setSimulations(response.data);
    } catch (error) {
      console.error('Failed to load simulations:', error);
    }
  };

  const initializeTechFields = async () => {
    try {
      await axios.post(`${API}/admin/init-tech-fields`);
    } catch (error) {
      console.error('Failed to initialize tech fields:', error);
    }
  };

  const initializeSimulations = async () => {
    try {
      await axios.post(`${API}/admin/init-simulations`);
    } catch (error) {
      console.error('Failed to initialize simulations:', error);
    }
  };

  const fetchTechFields = async () => {
    try {
      const response = await axios.get(`${API}/tech-fields`);
      setTechFields(response.data);
    } catch (error) {
      toast.error('Failed to load tech fields');
    }
  };

  const fetchSimulationsByField = async (fieldId) => {
    try {
      const response = await axios.get(`${API}/tech-fields/${fieldId}/simulations`);
      setSimulations(response.data);
    } catch (error) {
      toast.error('Failed to load simulations for this field');
    }
  };

  const downloadFile = async (simulationId) => {
    try {
      const response = await axios.get(`${API}/simulations/${simulationId}/file`);
      const { filename, content, mime_type } = response.data;
      
      // Decode base64 and create download
      const byteCharacters = atob(content);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: mime_type });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success(`Downloaded ${filename}`);
    } catch (error) {
      toast.error('Failed to download file');
    }
  };

  // Helper: storage key per simulation
  const getAttemptKey = (simId) => `sim_attempts_${simId}`;

  // When a simulation is selected, initialize engagement helpers
  useEffect(() => {
    if (!selectedSimulation) return;
    setRevealedHints(0);
    setChecklistState((selectedSimulation.checklist || []).map(() => false));
    setStartTime(Date.now());
    setElapsed(0);
    const key = getAttemptKey(selectedSimulation.id);
    const savedAttempts = parseInt(localStorage.getItem(key) || '0', 10);
    setAttempts(Number.isNaN(savedAttempts) ? 0 : savedAttempts);
    // Initialize question answers state
    const initialQA = {};
    const initialHints = {};
    (selectedSimulation.questions || []).forEach((q) => {
      initialQA[q.id] = '';
      initialHints[q.id] = 0;
    });
    setQuestionAnswers(initialQA);
    setQuestionHintsRevealed(initialHints);
    setQuestionResults({});
  }, [selectedSimulation]);

  // Timer ticker
  useEffect(() => {
    if (!startTime) return;
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, [startTime]);

  const formatElapsed = (total) => {
    const m = Math.floor(total / 60);
    const s = total % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const showAchievementNotification = (achievement) => {
    setShowAchievement(achievement);
    setTimeout(() => setShowAchievement(null), 3000);
  };

  const revealNextHint = () => {
    const totalHints = (selectedSimulation?.hints || []).length;
    if (revealedHints < totalHints) {
      setRevealedHints(revealedHints + 1);
      // Small penalty for using hints
      setTotalScore(prev => Math.max(0, prev - 5));
    }
  };

  const toggleChecklist = (idx) => {
    setChecklistState((prev) => {
      const next = [...prev];
      next[idx] = !next[idx];
      return next;
    });
  };

  const revealNextQuestionHint = (questionId) => {
    setQuestionHintsRevealed((prev) => {
      const next = { ...prev };
      const total = (selectedSimulation?.questions?.find((q) => q.id === questionId)?.hints || []).length;
      if ((next[questionId] || 0) < total) {
        next[questionId] = (next[questionId] || 0) + 1;
      }
      return next;
    });
  };

  const submitSingleQuestion = async (questionId) => {
    const answer = String(questionAnswers[questionId] || '').trim();
    if (!answer) {
      toast.error('Please answer this question');
      return;
    }
    setLoading(true);
    try {
      const payload = {
        simulation_id: selectedSimulation.id,
        answers: [{ question_id: questionId, answer }]
      };
      console.debug('Submitting single question payload:', payload);
      const response = await axios.post(
        `${API}/simulations/submit`,
        payload,
        { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
      );

      // Parse per-question feedback from submission.answer (JSON array)
      let perQ = [];
      try {
        perQ = JSON.parse(response.data.answer || '[]');
      } catch (e) {
        perQ = [];
      }
      const thisQ = perQ.find((p) => p.question_id === questionId);
      setQuestionResults((prev) => ({
        ...prev,
        [questionId]: {
          is_correct: thisQ ? thisQ.is_correct : response.data.is_correct,
          feedback: thisQ ? thisQ.feedback : response.data.ai_feedback
        }
      }));

      // Attempts bump
      const key = getAttemptKey(selectedSimulation.id);
      const nextAttempts = attempts + 1;
      localStorage.setItem(key, String(nextAttempts));
      setAttempts(nextAttempts);

      // Handle scoring and achievements
      const isCorrect = thisQ ? thisQ.is_correct : response.data.is_correct;
      if (isCorrect) {
        const points = 100 - (revealedHints * 10) - (attempts * 5);
        setTotalScore(prev => prev + Math.max(20, points));
        setStreakCount(prev => prev + 1);
        
        // Achievement notifications
        if (streakCount + 1 === 3) {
          showAchievementNotification({ title: "🔥 Hot Streak!", description: "3 correct answers in a row!" });
        } else if (streakCount + 1 === 5) {
          showAchievementNotification({ title: "⚡ Lightning Fast!", description: "5 correct answers in a row!" });
        }
        
        toast.success('🎯 Correct! Great job!');
      } else {
        setStreakCount(0);
        toast.error('❌ Not quite right, but keep trying!');
      }

      // If all questions are now correct, auto-finalize to award badge
      try {
        const allQs = (selectedSimulation.questions || []).map(q => q.id);
        const allCorrect = allQs.length > 0 && allQs.every(qid =>
          (qid === questionId ? (thisQ ? thisQ.is_correct : response.data.is_correct) : (questionResults[qid]?.is_correct))
        );
        if (allCorrect) {
          const answersArray = (selectedSimulation.questions || []).map((q) => ({
            question_id: q.id,
            answer: String((qid => (qid === questionId ? answer : (questionAnswers[qid] || '')))(q.id)).trim(),
          }));
          const finalizeResp = await axios.post(
            `${API}/simulations/submit`,
            { simulation_id: selectedSimulation.id, answers: answersArray },
            { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
          );
          // Show completion card on the simulation page
          setSubmission(finalizeResp.data);
          if (finalizeResp.data?.skill_badge_earned) {
            await fetchUser();
            showAchievementNotification({ 
              title: "🏆 Badge Earned!", 
              description: finalizeResp.data.skill_badge_earned 
            });
            toast.success(`🏆 Skill badge earned: ${finalizeResp.data.skill_badge_earned}!`);
          }
        }
      } catch (e) {
        console.warn('Auto-finalize skipped:', e?.response?.data || e?.message);
      }

      toast.success(thisQ && thisQ.is_correct ? 'Correct!' : 'Submitted');
    } catch (error) {
      const detail = error?.response?.data || error?.message;
      console.error('Submit single question error:', detail);
      try {
        const msg = typeof detail === 'string' ? detail : (detail?.detail ? JSON.stringify(detail.detail) : JSON.stringify(detail));
        toast.error(`Failed to submit: ${msg}`);
      } catch {
        toast.error('Failed to submit answer');
      }
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = async () => {
    setLoading(true);
    try {
      let payload;
      const hasQuestions = (selectedSimulation.questions || []).length > 0;
      if (hasQuestions) {
        const answersArray = (selectedSimulation.questions || []).map((q) => ({
          question_id: q.id,
          answer: String(questionAnswers[q.id] || '').trim(),
        }));
        // Basic validation: ensure none empty
        if (answersArray.some((a) => !a.answer)) {
          setLoading(false);
          toast.error('Please answer all questions');
          return;
        }
        payload = { simulation_id: selectedSimulation.id, answers: answersArray };
      } else {
        if (!userAnswer.trim()) {
          setLoading(false);
          toast.error('Please enter an answer');
          return;
        }
        payload = { simulation_id: selectedSimulation.id, answer: userAnswer.trim() };
      }

      const response = await axios.post(
        `${API}/simulations/submit`,
        payload,
        { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
      );

      setSubmission(response.data);
      // Increment attempts
      const key = getAttemptKey(selectedSimulation.id);
      const nextAttempts = attempts + 1;
      localStorage.setItem(key, String(nextAttempts));
      setAttempts(nextAttempts);

      // Refresh user data to update badges and completed simulations
      await fetchUser();

      if (response.data.skill_badge_earned) {
        toast.success(`🏆 Skill badge earned: ${response.data.skill_badge_earned}!`);
        toast.message('Great job!', { description: 'You completed this simulation successfully.' });
      } else {
        toast.success('Answer submitted!');
      }
    } catch (error) {
      toast.error('Failed to submit answer');
    } finally {
      setLoading(false);
    }
  };

  const getDifficultyColor = (difficulty) => {
    switch (difficulty.toLowerCase()) {
      case 'easy': return 'bg-green-100 text-green-700 border-green-200';
      case 'medium': return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      case 'hard': return 'bg-red-100 text-red-700 border-red-200';
      default: return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  // Tech Field View - Show simulations for selected field
  if (selectedField && !selectedSimulation) {
    return (
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white border-b sticky top-0 z-50">
          <div className="container mx-auto px-4 py-4 flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <Button
                variant="outline"
                onClick={async () => {
                  setSelectedField(null);
                  setSimulations([]);
                  // Refresh user data to show updated progress
                  await fetchUser();
                }}
              >
                ← Back to Tech Fields
              </Button>
              <div className="flex items-center space-x-3">
                <span className="text-2xl">{selectedField.icon}</span>
                <h1 className="text-xl font-semibold">{selectedField.name}</h1>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <BadgesNav />
              <Button variant="outline" onClick={logout}>
                <User className="h-4 w-4 mr-2" />
                {user.username}
              </Button>
            </div>
          </div>
        </header>

        <div className="container mx-auto px-4 py-8">
          <div className="max-w-6xl mx-auto">
            {/* Field Description */}
            <Card className="mb-8">
              <CardContent className="p-6">
                <p className="text-lg text-gray-700">{selectedField.description}</p>
              </CardContent>
            </Card>

            {/* Simulations Grid */}
            <Card>
              <CardHeader>
                <CardTitle>Available Tasks</CardTitle>
                <CardDescription>
                  Choose a task to start exploring {selectedField.name}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 gap-6">
                  {simulations.map((sim) => {
                    const isCompleted = user.completed_simulations.includes(sim.id);
                    return (
                      <Card key={sim.id} className="border-2 hover:border-orange-300 transition-colors cursor-pointer">
                        <CardHeader>
                          <div className="flex justify-between items-start">
                            <div>
                              <CardTitle className="text-lg">{sim.title}</CardTitle>
                              <CardDescription className="mt-1">
                                {sim.description}
                              </CardDescription>
                              <Badge variant="outline" className="mt-2">
                                {sim.sub_field}
                              </Badge>
                            </div>
                            {isCompleted && (
                              <CheckCircle className="h-5 w-5 text-green-600" />
                            )}
                          </div>
                        </CardHeader>
                        <CardContent>
                          <div className="flex justify-between items-center mb-4">
                            <Badge className={getDifficultyColor(sim.difficulty)}>
                              {sim.difficulty}
                            </Badge>
                            <div className="flex items-center text-sm text-gray-600">
                              <Clock className="h-4 w-4 mr-1" />
                              {sim.estimated_time}
                            </div>
                          </div>
                          <Button 
                            onClick={() => setSelectedSimulation(sim)}
                            className="w-full"
                            variant={isCompleted ? "outline" : "default"}
                          >
                            {isCompleted ? 'Try Again' : 'Start Task'}
                            <ArrowRight className="ml-2 h-4 w-4" />
                          </Button>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    );
  }

  if (selectedSimulation) {
    return (
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white border-b sticky top-0 z-50">
          <div className="container mx-auto px-4 py-4 flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <Button
                variant="outline"
                onClick={async () => {
                  setSelectedSimulation(null);
                  setSubmission(null);
                  setUserAnswer('');
                  setStartTime(null);
                  // Refresh user data to show updated progress
                  await fetchUser();
                }}
              >
                ← Back to {selectedField?.name || 'Tech Fields'}
              </Button>
              <h1 className="text-xl font-semibold flex items-center">
                {selectedSimulation.title}
                {selectedSimulation.title.includes('🚨') && <AlertTriangle className="h-5 w-5 text-red-500 ml-2 animate-pulse" />}
                {selectedSimulation.title.includes('🕵️') && <Shield className="h-5 w-5 text-blue-500 ml-2" />}
                {selectedSimulation.title.includes('🤖') && <Zap className="h-5 w-5 text-purple-500 ml-2" />}
                {selectedSimulation.title.includes('🐳') && <Rocket className="h-5 w-5 text-cyan-500 ml-2" />}
              </h1>
              <div className="hidden md:flex items-center text-sm text-gray-600 space-x-3">
                <div className="flex items-center space-x-1">
                  <Timer className="h-4 w-4" />
                  <span className={elapsed > 1200 ? 'text-red-600 font-bold animate-pulse' : elapsed > 600 ? 'text-orange-600 font-semibold' : 'text-green-600'}>
                    {formatElapsed(elapsed)}
                  </span>
                </div>
                <span>•</span>
                <div className="flex items-center space-x-1">
                  <Flame className="h-4 w-4" />
                  <span>Attempts: {attempts}</span>
                </div>
                <span>•</span>
                <div className="flex items-center space-x-1">
                  <Star className="h-4 w-4 text-yellow-500" />
                  <span className="font-semibold text-yellow-600">Score: {totalScore}</span>
                </div>
                {streakCount > 0 && (
                  <>
                    <span>•</span>
                    <div className="flex items-center space-x-1">
                      <Zap className="h-4 w-4 text-orange-500" />
                      <span className="font-semibold text-orange-600 animate-pulse">Streak: {streakCount}</span>
                    </div>
                  </>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <BadgesNav />
              <Button variant="outline" onClick={logout}>
                <User className="h-4 w-4 mr-2" />
                {user.username}
              </Button>
            </div>
          </div>
        </header>

        {/* Achievement Notification */}
        {showAchievement && (
          <div className="fixed top-20 right-4 z-50 bg-gradient-to-r from-yellow-400 to-orange-500 text-white p-4 rounded-lg shadow-lg animate-bounce">
            <div className="flex items-center space-x-2">
              <Trophy className="h-6 w-6" />
              <div>
                <div className="font-bold">{showAchievement.title}</div>
                <div className="text-sm">{showAchievement.description}</div>
              </div>
            </div>
          </div>
        )}

        <div className="container mx-auto px-4 py-8">
          <div className="max-w-4xl mx-auto">
            <Card className="mb-8 border-2 border-orange-200 shadow-lg">
              <CardHeader className="bg-gradient-to-r from-orange-50 to-red-50">
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-2xl flex items-center">
                      {selectedSimulation.title}
                      {selectedSimulation.title.includes('URGENT') && <AlertTriangle className="h-6 w-6 text-red-500 ml-2 animate-bounce" />}
                    </CardTitle>
                    <CardDescription className="mt-2 text-base font-medium">
                      {selectedSimulation.description}
                    </CardDescription>
                    {/* Progress Bar */}
                    <div className="mt-4">
                      <div className="flex justify-between text-sm text-gray-600 mb-1">
                        <span>Mission Progress</span>
                        <span>{Math.min(100, Math.floor((elapsed / (parseFloat(selectedSimulation.estimated_time) * 60)) * 100))}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className={`h-2 rounded-full transition-all duration-1000 ${
                            elapsed > parseFloat(selectedSimulation.estimated_time) * 60 
                              ? 'bg-red-500 animate-pulse' 
                              : elapsed > parseFloat(selectedSimulation.estimated_time) * 60 * 0.8 
                                ? 'bg-orange-500' 
                                : 'bg-green-500'
                          }`}
                          style={{ 
                            width: `${Math.min(100, Math.floor((elapsed / (parseFloat(selectedSimulation.estimated_time) * 60)) * 100))}%` 
                          }}
                        ></div>
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-col items-end space-y-2">
                    <Badge className={getDifficultyColor(selectedSimulation.difficulty)}>
                      {selectedSimulation.difficulty}
                    </Badge>
                    <div className="flex items-center text-sm text-gray-600">
                      <Clock className="h-4 w-4 mr-1" />
                      {selectedSimulation.estimated_time}
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <h3 className="font-semibold text-lg mb-3">📋 Briefing</h3>
                  <p className="text-gray-700 leading-relaxed">{selectedSimulation.briefing}</p>
                </div>
                
                <Separator />
                
                <div>
                  <h3 className="font-semibold text-lg mb-3">📝 Instructions</h3>
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <pre className="whitespace-pre-wrap text-sm text-gray-700 font-medium">
                      {selectedSimulation.instructions}
                    </pre>
                  </div>
                </div>

                {(selectedSimulation.hints?.length || 0) > 0 && (
                  <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold text-orange-900">💡 Hints</h3>
                      <Button size="sm" variant="outline" onClick={revealNextHint} disabled={revealedHints >= (selectedSimulation.hints?.length || 0)}>
                        {revealedHints < (selectedSimulation.hints?.length || 0) ? 'Reveal next hint' : 'All hints shown'}
                      </Button>
                    </div>
                    <ul className="list-disc pl-5 space-y-1">
                      {(selectedSimulation.hints || []).slice(0, revealedHints).map((hint, idx) => (
                        <li key={idx} className="text-sm text-orange-900">{hint}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {(selectedSimulation.checklist?.length || 0) > 0 && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <h3 className="font-semibold text-green-900 mb-2">✅ Progress Checklist</h3>
                    <ul className="space-y-2">
                      {(selectedSimulation.checklist || []).map((item, idx) => (
                        <li key={idx} className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            checked={!!checklistState[idx]}
                            onChange={() => toggleChecklist(idx)}
                          />
                          <span className="text-sm text-green-900">{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="flex justify-center">
                  <Button
                    onClick={() => downloadFile(selectedSimulation.id)}
                    className="bg-orange-600 hover:bg-orange-700"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download Required Files
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Questions & Submission Area */}
            {!submission ? (
              <Card>
                <CardHeader>
                  <CardTitle>{(selectedSimulation.questions || []).length > 0 ? 'Answer the Questions' : 'Submit Your Answer'}</CardTitle>
                  <CardDescription>
                    {(selectedSimulation.questions || []).length > 0
                      ? 'Answer all questions and click submit to get AI-powered feedback'
                      : 'Enter your answer below and click submit to get AI-powered feedback'}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {(selectedSimulation.questions || []).length > 0 ? (
                      <div className="space-y-4">
                        {(selectedSimulation.questions || []).map((q) => {
                          const revealed = questionHintsRevealed[q.id] || 0;
                          const totalHints = (q.hints || []).length;
                          const result = questionResults[q.id];
                          return (
                          <div key={q.id} className={`border rounded-md p-3 transition-all duration-300 ${
                            result?.is_correct 
                              ? 'bg-green-50 border-green-300 shadow-lg' 
                              : result && !result.is_correct 
                                ? 'bg-red-50 border-red-300' 
                                : 'bg-white border-gray-200 hover:border-orange-300'
                          }`}>
                              <div className="flex items-start justify-between">
                                <div className="flex-1 pr-4">
                                  <Label htmlFor={`q_${q.id}`} className="flex items-center">
                                    {q.prompt}
                                    {result?.is_correct && <CheckCircle className="h-4 w-4 text-green-600 ml-2" />}
                                    {result && !result.is_correct && <AlertTriangle className="h-4 w-4 text-red-600 ml-2" />}
                                  </Label>
                                  <Input
                                    id={`q_${q.id}`}
                                    value={questionAnswers[q.id] || ''}
                                    onChange={(e) => {
                                      const input = e.target.value;
                                      const maxLen = q.max_length || 0;
                                      const next = maxLen > 0 ? input.slice(0, maxLen) : input;
                                      setQuestionAnswers({ ...questionAnswers, [q.id]: next });
                                    }}
                                    placeholder={q.answer_mask || 'Enter your answer...'}
                                    maxLength={q.max_length || undefined}
                                    className={`mt-2 transition-all duration-200 ${
                                      result?.is_correct 
                                        ? 'border-green-400 bg-green-50' 
                                        : result && !result.is_correct 
                                          ? 'border-red-400 bg-red-50' 
                                          : 'border-gray-300 focus:border-orange-400'
                                    }`}
                                    disabled={result?.is_correct}
                                  />
                                </div>
                                <div className="flex items-center space-x-2">
                                  {totalHints > 0 && (
                                    <Button 
                                      size="sm" 
                                      variant="outline" 
                                      onClick={() => revealNextQuestionHint(q.id)} 
                                      disabled={revealed >= totalHints || result?.is_correct}
                                      className="hover:bg-orange-50"
                                    >
                                      💡 {revealed < totalHints ? `Hint (${totalHints - revealed} left)` : 'All hints shown'}
                                    </Button>
                                  )}
                                  <Button 
                                    size="sm" 
                                    onClick={() => submitSingleQuestion(q.id)} 
                                    disabled={loading || result?.is_correct} 
                                    className={`transition-all duration-200 ${
                                      result?.is_correct 
                                        ? 'bg-green-600 hover:bg-green-700' 
                                        : 'bg-blue-600 hover:bg-blue-700'
                                    } text-white`}
                                  >
                                    {result?.is_correct ? '✅ Correct!' : '🚀 Submit'}
                                  </Button>
                                </div>
                              </div>
                              {revealed > 0 && (
                                <ul className="list-disc pl-5 mt-2 space-y-1 text-sm text-orange-900">
                                  {(q.hints || []).slice(0, revealed).map((h, i) => (
                                    <li key={i}>{h}</li>
                                  ))}
                                </ul>
                              )}
                              {result && (
                                <div className={`mt-2 rounded-md p-3 text-sm transition-all duration-300 ${
                                  result.is_correct 
                                    ? 'bg-green-50 border border-green-200 text-green-900 shadow-md' 
                                    : 'bg-blue-50 border border-blue-200 text-blue-900'
                                }`}>
                                  <div className="flex items-start space-x-2">
                                    {result.is_correct ? (
                                      <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 animate-pulse" />
                                    ) : (
                                      <Brain className="h-5 w-5 text-blue-600 mt-0.5" />
                                    )}
                                    <div>
                                      <div className="font-semibold">
                                        {result.is_correct ? '🎉 Excellent work!' : '💭 AI Feedback:'}
                                      </div>
                                      <div className="mt-1">
                                        {result.feedback || (result.is_correct ? 'Perfect answer! You nailed it!' : 'Keep trying - you\'re on the right track!')}
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div>
                        <Label htmlFor="answer">Your Answer</Label>
                        <Input
                          id="answer"
                          value={userAnswer}
                          onChange={(e) => setUserAnswer(e.target.value)}
                          placeholder="Enter your answer here..."
                          className="mt-2"
                        />
                      </div>
                    )}
                    {((selectedSimulation.questions || []).length === 0) && (
                      <Button 
                        onClick={submitAnswer} 
                        disabled={loading}
                        className="bg-green-600 hover:bg-green-700"
                      >
                        <Send className="h-4 w-4 mr-2" />
                        {loading ? 'Submitting...' : 'Submit Answer'}
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <CheckCircle className="h-5 w-5 mr-2 text-green-600" />
                    Submission Complete!
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {(() => {
                    const hasQuestions = (selectedSimulation.questions || []).length > 0;
                    if (!hasQuestions) {
                      return (
                        <div>
                          <Label>Your Answer:</Label>
                          <p className="font-semibold text-lg">{submission.answer}</p>
                        </div>
                      );
                    }
                    let parsed = [];
                    try {
                      parsed = JSON.parse(submission.answer || '[]');
                    } catch (e) {
                      parsed = [];
                    }
                    return (
                      <div>
                        <Label>Your Answers:</Label>
                        <div className="mt-2 space-y-3">
                          {parsed.map((item, idx) => (
                            <div key={idx} className={`border rounded-md p-3 ${item.is_correct ? 'border-green-200 bg-green-50' : 'border-yellow-200 bg-yellow-50'}`}>
                              <div className="flex items-center justify-between">
                                <div className="text-sm text-gray-800">
                                  <span className="font-medium">Q: </span>
                                  {selectedSimulation.questions?.find(q => q.id === item.question_id)?.prompt || item.question_id}
                                </div>
                                <Badge className={item.is_correct ? 'bg-green-600 text-white' : 'bg-yellow-600 text-white'}>
                                  {item.is_correct ? 'Correct' : 'Submitted'}
                                </Badge>
                              </div>
                              <div className="mt-2 text-sm">
                                <span className="font-medium">Your answer: </span>
                                <span>{item.answer}</span>
                              </div>
                              {item.feedback && (
                                <div className="mt-2 text-sm text-gray-800">
                                  <span className="font-medium">Feedback: </span>
                                  <span>{item.feedback}</span>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })()}
                  
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <Label className="text-blue-900 font-semibold">🤖 AI Feedback:</Label>
                    <p className="mt-2 text-blue-800">{submission.ai_feedback}</p>
                  </div>

                  {submission.skill_badge_earned && (
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                      <div className="flex items-center">
                        <Trophy className="h-5 w-5 text-yellow-600 mr-2" />
                        <span className="font-semibold text-yellow-800">
                          New Skill Badge: {submission.skill_badge_earned}
                        </span>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <Target className="h-8 w-8 text-orange-600" />
            <h1 className="text-2xl font-bold text-gray-900">Project Pathfinder</h1>
          </div>
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <p className="text-sm font-medium">{user.username}</p>
            </div>
            <BadgesNav />
            <Button variant="outline" onClick={logout}>
              <User className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="max-w-6xl mx-auto">
          {/* Welcome Section */}
          <div className="mb-8">
            <h2 className="text-3xl font-bold text-gray-900 mb-2">
              Welcome back, {user.username}! 🎯
            </h2>
            <p className="text-gray-600">
              Ready to explore new careers? Choose a simulation below to get started.
            </p>
          </div>

          {/* User Stats */}
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            <Card>
              <CardContent className="p-6 text-center">
                <Trophy className="h-8 w-8 text-yellow-600 mx-auto mb-2" />
                <div className="text-2xl font-bold">{user.skill_badges.length}</div>
                <div className="text-sm text-gray-600">Badges</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6 text-center">
                <CheckCircle className="h-8 w-8 text-green-600 mx-auto mb-2" />
                <div className="text-2xl font-bold">{user.completed_simulations.length}</div>
                <div className="text-sm text-gray-600">Completed</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6 text-center">
                <BookOpen className="h-8 w-8 text-blue-600 mx-auto mb-2" />
                <div className="text-2xl font-bold">{Math.max(0, simulations.length - user.completed_simulations.length)}</div>
                <div className="text-sm text-gray-600">Available</div>
              </CardContent>
            </Card>
          </div>

          {/* Skill Badges list removed from Dashboard (badges now live on /badges page) */}

          {/* Tech Fields */}
          <Card>
            <CardHeader>
              <CardTitle>Tech Career Fields</CardTitle>
              <CardDescription>
                Choose a tech field to explore different career paths and specializations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {techFields.map((field) => {
                  // For now, show placeholder data since we don't have all simulations loaded
                  const fieldSimulations = simulations.filter(sim => sim.field_id === field.id);
                  const completedInField = fieldSimulations.filter(sim => 
                    user.completed_simulations.includes(sim.id)
                  ).length;
                  
                  // Show 2 tasks per field as placeholder
                  const taskCount = fieldSimulations.length > 0 ? fieldSimulations.length : 2;
                  
                  return (
                    <Card 
                      key={field.id} 
                      className="border-2 hover:border-orange-300 transition-colors cursor-pointer"
                      onClick={() => {
                        setSelectedField(field);
                        fetchSimulationsByField(field.id);
                      }}
                    >
                      <CardHeader>
                        <div className="flex items-center space-x-3 mb-3">
                          <span className="text-3xl">{field.icon}</span>
                          <div>
                            <CardTitle className="text-lg">{field.name}</CardTitle>
                            <div className="flex items-center space-x-2 mt-1">
                              <Badge className={`bg-${field.color}-100 text-${field.color}-700 border-${field.color}-200`}>
                                {taskCount} tasks
                              </Badge>
                              {completedInField > 0 && (
                                <Badge className="bg-green-100 text-green-700 border-green-200">
                                  {completedInField} completed
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>
                        <CardDescription className="text-sm">
                          {field.description}
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <Button 
                          className="w-full"
                          variant="outline"
                        >
                          Explore {field.name}
                          <ArrowRight className="ml-2 h-4 w-4" />
                        </Button>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

// Small component: navigation button to Badges page
const BadgesNav = () => {
  const navigate = useNavigate();
  return (
    <Button variant="outline" onClick={() => navigate('/badges')}>
      <Trophy className="h-4 w-4 mr-2 text-yellow-600" />
      Badges
    </Button>
  );
};

 

// Badges Page Component
const BadgesPage = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <Button variant="outline" onClick={() => navigate('/dashboard')}>← Back</Button>
            <h1 className="text-xl font-semibold flex items-center">
              <Trophy className="h-5 w-5 mr-2 text-yellow-600" /> Your Badges
            </h1>
          </div>
          <Button variant="outline" onClick={logout}>
            <User className="h-4 w-4 mr-2" />
            {user?.username}
          </Button>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">

          {/* Badges Grid */}
          {(user?.skill_badges || []).length > 0 && (
            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Trophy className="h-5 w-5 mr-2 text-yellow-600" /> Badges
                </CardTitle>
                <CardDescription>A showcase of your achievements</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 gap-4">
                  {user.skill_badges.map((name, idx) => {
                    const meta = BADGE_META[name] || { 
                      icon: '🏅', 
                      color: 'from-gray-50 to-slate-50', 
                      description: `Earned for completing the "${name}" simulation`,
                      rarity: 'Common',
                      rarityPct: ''
                    };
                    return (
                      <div key={idx} className="relative flex items-center p-4 rounded-xl border bg-white hover:shadow-md transition-shadow">
                        {/* Emblem */}
                        <div className={`h-16 w-16 mr-4 rounded-xl bg-gradient-to-br ${meta.color} flex items-center justify-center text-2xl`}>
                          <span aria-hidden>{meta.icon}</span>
                        </div>
                        {/* Text */}
                        <div className="flex-1">
                          <div className="font-semibold text-gray-900">{name}</div>
                          <div className="text-sm text-gray-600 mt-0.5">{meta.description}</div>
                          <div className="mt-2 flex items-center gap-2">
                            <span className={`text-xs px-2 py-0.5 rounded-full border ${meta.rarity === 'Rare' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-blue-50 text-blue-700 border-blue-200'}`}>
                              {meta.rarity}{meta.rarityPct ? `: ${meta.rarityPct}` : ''}
                            </span>
                          </div>
                        </div>
                        {/* Completed check */}
                        <div className="absolute bottom-2 right-2 bg-green-600 rounded-full p-1">
                          <CheckCircle className="h-4 w-4 text-white" />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>How to earn more badges</CardTitle>
              <CardDescription>Pick simulations from different fields and complete all questions correctly.</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="list-disc pl-5 space-y-1 text-gray-700">
                <li>Complete all questions in a simulation to unlock its badge.</li>
                <li>Use hints strategically to learn, but aim for fewer attempts for higher scores.</li>
                <li>Explore multiple fields to diversify your badge collection.</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

// Main App Component
function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Target className="h-12 w-12 text-orange-600 mx-auto mb-4 animate-spin" />
          <p className="text-gray-600">Loading Project Pathfinder...</p>
        </div>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <div className="App">
        <Toaster position="top-right" />
        <Routes>
          <Route
            path="/"
            element={user ? <Navigate to="/dashboard" replace /> : <LandingPage />}
          />
          <Route
            path="/dashboard"
            element={user ? <Dashboard /> : <Navigate to="/" replace />}
          />
          <Route
            path="/badges"
            element={user ? <BadgesPage /> : <Navigate to="/" replace />}
          />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

function AppWithAuth() {
  return (
    <AuthProvider>
      <App />
    </AuthProvider>
  );
}

export default AppWithAuth;