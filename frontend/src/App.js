import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
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
  BarChart3
} from 'lucide-react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

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
    <AuthContext.Provider value={{ user, token, login, register, logout, loading }}>
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
                Discover careers by 
                <span className="text-orange-600 block">actually doing the work</span>
              </h2>
              <p className="text-xl text-gray-600 leading-relaxed">
                Skip the confusing personality quizzes. Complete hands-on simulations that mirror real jobs and get instant AI feedback to discover what truly excites you.
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
                  <h4 className="font-semibold text-gray-900">Real-World Tasks</h4>
                  <p className="text-sm text-gray-600">Work with actual business scenarios and industry tools</p>
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
  const { user, logout } = useAuth();
  const [simulations, setSimulations] = useState([]);
  const [selectedSimulation, setSelectedSimulation] = useState(null);
  const [userAnswer, setUserAnswer] = useState('');
  const [submission, setSubmission] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchSimulations();
    initializeSimulations();
  }, []);

  const initializeSimulations = async () => {
    try {
      await axios.post(`${API}/admin/init-simulations`);
    } catch (error) {
      console.error('Failed to initialize simulations:', error);
    }
  };

  const fetchSimulations = async () => {
    try {
      const response = await axios.get(`${API}/simulations`);
      setSimulations(response.data);
    } catch (error) {
      toast.error('Failed to load simulations');
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

  const submitAnswer = async () => {
    if (!userAnswer.trim()) {
      toast.error('Please enter an answer');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(
        `${API}/simulations/submit`,
        {
          simulation_id: selectedSimulation.id,
          answer: userAnswer.trim()
        },
        {
          headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
        }
      );
      
      setSubmission(response.data);
      if (response.data.skill_badge_earned) {
        toast.success(`🏆 Skill badge earned: ${response.data.skill_badge_earned}!`);
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

  if (selectedSimulation) {
    return (
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white border-b sticky top-0 z-50">
          <div className="container mx-auto px-4 py-4 flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <Button
                variant="outline"
                onClick={() => {
                  setSelectedSimulation(null);
                  setSubmission(null);
                  setUserAnswer('');
                }}
              >
                ← Back to Dashboard
              </Button>
              <h1 className="text-xl font-semibold">{selectedSimulation.title}</h1>
            </div>
            <Button variant="outline" onClick={logout}>
              <User className="h-4 w-4 mr-2" />
              {user.username}
            </Button>
          </div>
        </header>

        <div className="container mx-auto px-4 py-8">
          <div className="max-w-4xl mx-auto">
            <Card className="mb-8">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-2xl">{selectedSimulation.title}</CardTitle>
                    <CardDescription className="mt-2 text-base">
                      {selectedSimulation.description}
                    </CardDescription>
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

            {/* Submission Area */}
            {!submission ? (
              <Card>
                <CardHeader>
                  <CardTitle>Submit Your Answer</CardTitle>
                  <CardDescription>
                    Enter your answer below and click submit to get AI-powered feedback
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
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
                    <Button 
                      onClick={submitAnswer} 
                      disabled={loading}
                      className="bg-green-600 hover:bg-green-700"
                    >
                      <Send className="h-4 w-4 mr-2" />
                      {loading ? 'Submitting...' : 'Submit Answer'}
                    </Button>
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
                  <div>
                    <Label>Your Answer:</Label>
                    <p className="font-semibold text-lg">{submission.answer}</p>
                  </div>
                  
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
              <p className="text-xs text-gray-600">{user.skill_badges.length} badges earned</p>
            </div>
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
                <div className="text-sm text-gray-600">Skill Badges</div>
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
                <div className="text-2xl font-bold">{simulations.length - user.completed_simulations.length}</div>
                <div className="text-sm text-gray-600">Available</div>
              </CardContent>
            </Card>
          </div>

          {/* Skill Badges */}
          {user.skill_badges.length > 0 && (
            <Card className="mb-8">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Trophy className="h-5 w-5 mr-2 text-yellow-600" />
                  Your Skill Badges
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {user.skill_badges.map((badge, index) => (
                    <Badge key={index} className="bg-yellow-100 text-yellow-800 border-yellow-300">
                      🏆 {badge}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Simulations */}
          <Card>
            <CardHeader>
              <CardTitle>Career Simulations</CardTitle>
              <CardDescription>
                Choose a simulation to start exploring different career paths
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
                        <Badge variant="outline" className="mb-4">
                          {sim.category}
                        </Badge>
                        <Button 
                          onClick={() => setSelectedSimulation(sim)}
                          className="w-full"
                          variant={isCompleted ? "outline" : "default"}
                        >
                          {isCompleted ? 'Try Again' : 'Start Simulation'}
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