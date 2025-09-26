from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta, timezone
import jwt
from passlib.context import CryptContext
import pandas as pd
import io
import base64
import json
import hashlib
import random
# Local feedback system (no external AI dependencies)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
if SECRET_KEY == 'your-secret-key-change-in-production':
    print("WARNING: Using default JWT_SECRET. Set JWT_SECRET environment variable for production.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app without a prefix
app = FastAPI(title="Project Pathfinder API")

# Add CORS middleware for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Pydantic Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    username: str
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    skill_badges: List[str] = Field(default_factory=list)
    completed_simulations: List[str] = Field(default_factory=list)

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserProfile(BaseModel):
    id: str
    email: str
    username: str
    skill_badges: List[str]
    completed_simulations: List[str]
    created_at: datetime

class TechField(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    icon: str
    color: str

class Question(BaseModel):
    id: str
    prompt: str
    expected_answer_type: str  # "number", "text", "percentage", "list", "code", "boolean"
    # Store correct answer server-side only; do not expose in public response
    correct_answer: Optional[str] = None
    hints: List[str] = Field(default_factory=list)


class QuestionPublic(BaseModel):
    id: str
    prompt: str
    expected_answer_type: str
    hints: List[str] = Field(default_factory=list)
    # UI helpers (do not reveal actual answer content)
    answer_mask: Optional[str] = None
    max_length: Optional[int] = None


class Simulation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    field_id: str  # References TechField
    sub_field: str  # e.g., "Development", "Debugging", "Testing"
    difficulty: str
    estimated_time: str
    briefing: str
    instructions: str
    task_type: str  # "calculation", "analysis", "find_value", "security", "research", "debugging", "development"
    expected_answer_type: str  # "number", "text", "percentage", "list", "code"
    # Optional engagement helpers
    hints: List[str] = Field(default_factory=list)
    checklist: List[str] = Field(default_factory=list)
    # Optional multi-question support
    questions: List[Question] = Field(default_factory=list)


class SimulationPublic(BaseModel):
    id: str
    title: str
    description: str
    field_id: str
    sub_field: str
    difficulty: str
    estimated_time: str
    briefing: str
    instructions: str
    task_type: str
    expected_answer_type: str
    hints: List[str] = Field(default_factory=list)
    checklist: List[str] = Field(default_factory=list)
    # Expose questions without correct answers
    questions: List[QuestionPublic] = Field(default_factory=list)

class SimulationSubmission(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    simulation_id: str
    answer: str
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ai_feedback: Optional[str] = None
    is_correct: Optional[bool] = None
    skill_badge_earned: Optional[str] = None


class SubmissionCreate(BaseModel):
    simulation_id: str
    answer: Optional[str] = None
    # Accept a loose payload to avoid validation 422 from clients
    answers: Optional[List[Dict[str, Any]]] = None

class FileDownload(BaseModel):
    filename: str
    content: str  # base64 encoded
    mime_type: str

 

# Authentication Functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"id": user_id})
    if user is None:
        raise credentials_exception
    return User(**user)

@api_router.get("/health")
async def health_check():
    return {"status": "ok", "service": "Project Pathfinder API"}

 

# Local Feedback System
async def generate_ai_feedback(simulation_id: str, user_answer: str, correct_answer: str = None) -> Dict[str, Any]:
    """Generate local feedback without external AI dependencies"""
    try:
        # Get simulation details
        simulation = await db.simulations.find_one({"id": simulation_id})
        if not simulation:
            return {"feedback": "Simulation not found", "is_correct": False}
        
        # Enhanced correctness checking based on simulation type
        is_correct = False
        if correct_answer:
            user_clean = str(user_answer).lower().strip()
            correct_clean = str(correct_answer).lower().strip()
            
            # Specific logic for each simulation type
            if simulation_id == 'cyber-password-1':
                # Multiple passwords - need at least 2 correct
                expected_passwords = [p.strip().lower() for p in correct_answer.split(',')]
                user_input = user_answer.replace(' ', '').lower()  # Remove spaces
                user_passwords = [p.strip().lower() for p in user_input.split(',')]
                
                matches = set(user_passwords) & set(expected_passwords)
                is_correct = len(matches) >= 2
                
            elif simulation_id in ['ds-modeling-1']:
                # Percentage answers - handle various formats
                try:
                    user_numeric = user_clean.replace('%', '').replace(' ', '')
                    correct_numeric = correct_clean.replace('%', '').replace(' ', '')
                    
                    # Try exact match first
                    if user_numeric == correct_numeric:
                        is_correct = True
                    else:
                        # Try float comparison with small tolerance
                        user_val = float(user_numeric)
                        correct_val = float(correct_numeric)
                        is_correct = abs(user_val - correct_val) < 0.01
                except Exception:
                    is_correct = user_clean == correct_clean
                    
            elif simulation_id in ['se-debugging-1', 'se-development-1', 'se-testing-1', 'devops-deployment-1', 'devops-monitoring-1', 'cloud-aws-1', 'cloud-security-1', 'mobile-native-1', 'mobile-cross-1']:
                # Numeric answers
                try:
                    user_num = int(user_clean)
                    correct_num = int(correct_clean)
                    is_correct = user_num == correct_num
                except Exception:
                    is_correct = user_clean == correct_clean
                    
            elif simulation_id == 'cyber-penetration-1':
                # Vulnerability type - check for key terms
                vulnerability_terms = ['default_credentials', 'default credentials', 'weak password', 'weak_password']
                is_correct = any(term in user_clean for term in vulnerability_terms)
                
            elif simulation_id == 'ds-analysis-1':
                # Feature name - check for monthly charges
                feature_terms = ['monthly_charges', 'monthly charges', 'monthlycharges']
                is_correct = any(term in user_clean for term in feature_terms)
                    
            else:
                # Default exact match
                is_correct = user_clean == correct_clean
        else:
            is_correct = False
        
        # Generate contextual feedback based on simulation type and correctness
        feedback_templates = {
            # Software Engineering
            'se-debugging-1': {
                'correct': "Excellent debugging skills! You've identified all 5 critical bugs in the shopping cart code. This type of systematic code review is essential for software engineers who need to maintain code quality and prevent production issues.",
                'incorrect': "Good effort on the debugging challenge! There are 5 bugs: (1) assignment vs comparison operator (= instead of ==), (2) missing negative discount validation, (3) no minimum order validation, (4) race condition in cart updates, (5) missing null check for empty cart. Keep practicing code review skills!"
            },
            'se-development-1': {
                'correct': "Perfect! You've correctly identified HTTP 200 as the success status code for login. Understanding HTTP status codes and API design is fundamental for backend developers building robust web services.",
                'incorrect': "Good attempt at the API development task! The correct HTTP status code for successful login is 200. This indicates the request was processed successfully and the user is authenticated."
            },
            'se-testing-1': {
                'correct': "Outstanding! You've identified 7 comprehensive test cases for the calculator class. This shows strong QA engineering skills - thorough testing is crucial for ensuring software reliability and preventing bugs in production.",
                'incorrect': "Good effort on the testing challenge! The calculator class needs 7 test cases: basic arithmetic, division by zero, square root of negatives, history tracking, edge cases, input validation, and memory management."
            },
            
            # Cybersecurity
            'cyber-password-1': {
                'correct': "Excellent security analysis! You've successfully cracked the weak passwords, demonstrating strong cybersecurity skills. This type of password security assessment is crucial for security professionals protecting organizational data.",
                'incorrect': "Good attempt at the password security challenge! The cracked passwords are: password123, admin, letmein. These are common weak passwords that should be avoided in production systems."
            },
            'cyber-penetration-1': {
                'correct': "Perfect! You've identified default credentials as the most critical vulnerability. This shows strong penetration testing skills - default credentials are often the easiest entry point for attackers and should be the first thing to secure.",
                'incorrect': "Good effort on the penetration testing task! The most critical vulnerability is 'default credentials' - the router is using admin/admin123 which is easily guessable and should be changed immediately."
            },
            
            # Data Science
            'ds-analysis-1': {
                'correct': "Excellent data analysis! You've correctly identified Monthly_Charges as the strongest predictor of customer churn. This type of feature analysis is crucial for data scientists building predictive models and business intelligence systems.",
                'incorrect': "Good attempt at the churn analysis! The strongest predictor is 'Monthly_Charges' - customers with higher monthly charges are more likely to churn, making this a key feature for retention strategies."
            },
            'ds-modeling-1': {
                'correct': "Outstanding! You've achieved 85% accuracy on the email spam classifier, demonstrating strong machine learning skills. This level of accuracy is excellent for a production spam filter and shows good model selection and feature engineering.",
                'incorrect': "Good effort on the ML pipeline! The target accuracy is 85% - this requires proper text preprocessing, feature extraction, and model selection. Try different algorithms like Naive Bayes or SVM for better results."
            },
            
            # DevOps
            'devops-deployment-1': {
                'correct': "Perfect! You've correctly identified 4 Docker layers for the web application. This shows strong containerization skills - understanding Docker layer optimization is crucial for DevOps engineers building efficient deployment pipelines.",
                'incorrect': "Good attempt at the Docker containerization! The optimal Dockerfile should have 4 layers: base image, dependencies, application code, and runtime configuration. This minimizes image size and improves build performance."
            },
            'devops-monitoring-1': {
                'correct': "Excellent monitoring setup! You've identified 6 essential monitoring rules for the production application. This shows strong SRE skills - comprehensive monitoring is crucial for maintaining system reliability and quickly detecting issues.",
                'incorrect': "Good effort on the monitoring configuration! You need 6 monitoring rules: high response time, high error rate, high resource usage, service down, database failures, and memory leaks. Each rule should have appropriate thresholds and alerting."
            },
            
            # Cloud Computing
            'cloud-aws-1': {
                'correct': "Outstanding! You've correctly identified 12 AWS services needed for the multi-tier architecture. This shows strong cloud architecture skills - understanding service selection and integration is crucial for building scalable cloud solutions.",
                'incorrect': "Good attempt at the AWS architecture! You need 12 services: EC2, RDS, S3, CloudFront, ALB, Auto Scaling, VPC, IAM, CloudWatch, Route 53, SNS, and Lambda. Each service serves a specific purpose in the architecture."
            },
            'cloud-security-1': {
                'correct': "Perfect! You've identified 5 security groups needed for the multi-tier architecture. This shows strong cloud security skills - proper network segmentation is crucial for protecting cloud resources and implementing defense in depth.",
                'incorrect': "Good effort on the cloud security configuration! You need 5 security groups: web tier, application tier, database tier, bastion host, and load balancer. Each should have restrictive rules following least privilege principles."
            },
            
            # Mobile Development
            'mobile-native-1': {
                'correct': "Excellent performance analysis! You've identified all 8 performance issues in the iOS app code. This shows strong mobile development skills - performance optimization is crucial for creating smooth, responsive mobile applications.",
                'incorrect': "Good attempt at the iOS performance optimization! There are 8 issues: no cell reuse, main thread blocking, synchronous image loading, heavy computation, memory leaks, inefficient cell creation, unoptimized images, and poor memory management."
            },
            'mobile-cross-1': {
                'correct': "Perfect! You've identified 3 reducers needed for proper React Native state management. This shows strong mobile development skills - understanding state management patterns is crucial for building maintainable cross-platform applications.",
                'incorrect': "Good effort on the React Native state management! You need 3 reducers: userReducer (for user data), uiReducer (for UI state), and errorReducer (for error handling). This provides clean separation of concerns and better maintainability."
            },
            
            # Product Management
            'pm-strategy-1': {
                'correct': "Excellent product strategy! You've correctly identified 5 features for Q1 roadmap based on RICE scoring. This shows strong product management skills - prioritization and strategic thinking are crucial for successful product development.",
                'incorrect': "Good effort on the product roadmap planning! The correct answer is 5 features for Q1. Focus on features with highest RICE scores: User Authentication, Push Notifications, Data Export, Custom Themes, and Real-time Chat."
            },
            'pm-analytics-1': {
                'correct': "Outstanding analytics analysis! You've correctly identified 12.5% as the conversion rate. This shows strong product analytics skills - understanding key metrics is crucial for data-driven product decisions and growth optimization.",
                'incorrect': "Good attempt at the product metrics analysis! The correct conversion rate is 12.5%. This is a key metric that shows how well your product converts visitors into active users."
            },
            'pm-user-research-1': {
                'correct': "Perfect user research analysis! You've correctly identified 'slow_loading' as the most frequent pain point. This shows strong user research skills - identifying and prioritizing user pain points is crucial for product improvement and user satisfaction.",
                'incorrect': "Good effort on the user interview analysis! The most frequently mentioned pain point is 'slow_loading' - mentioned by 18 out of 20 users. This should be the top priority for product improvements."
            }
        }
        
        # Get appropriate feedback based on simulation and correctness
        template = feedback_templates.get(simulation_id, {
            'correct': f"Great work on the {simulation.get('category', 'career')} simulation! You've demonstrated strong skills in this area.",
            'incorrect': f"Good effort on the {simulation.get('category', 'career')} task! Review the instructions and try again - practice makes perfect."
        })
        
        response = template['correct'] if is_correct else template['incorrect']
        
        return {
            "feedback": response,
            "is_correct": is_correct
        }
    except Exception as e:
        logging.error(f"Feedback generation failed: {e}")
        return {
            "feedback": f"Great work completing this {simulation.get('category', 'career')} simulation! This hands-on experience helps you understand what this field involves day-to-day. Keep exploring different career paths to find what truly engages you.",
            "is_correct": True
        }

# File Generation Functions
def generate_business_analysis_file():
    """Generate a sales spreadsheet for business analysis simulation"""
    data = {
        'Product': ['Widget A', 'Widget B', 'Widget C', 'Service X', 'Service Y'],
        'Revenue': [25000, 18500, 31200, 12800, 22100],
        'Cost_of_Goods': [15000, 11000, 18500, 5200, 8900],
        'Operating_Expenses': [3200, 2800, 4100, 2400, 3800],
        'Marketing_Spend': [1500, 1200, 2000, 800, 1600],
        'Other_Expenses': [800, 600, 900, 400, 700]
    }
    
    df = pd.DataFrame(data)
    
    # Convert to Excel bytes
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, sheet_name='Sales_Data')
    excel_buffer.seek(0)
    
    return {
        'filename': 'Q3_Sales_Analysis.xlsx',
        'content': base64.b64encode(excel_buffer.getvalue()).decode(),
        'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }

def generate_marketing_analytics_file():
    """Generate an analytics report for digital marketing simulation"""
    data = {
        'Metric': [
            'Total Sessions',
            'Desktop Sessions', 
            'Mobile Sessions',
            'Tablet Sessions',
            'Desktop Bounce Rate',
            'Mobile Bounce Rate', 
            'Tablet Bounce Rate',
            'Avg Session Duration',
            'Page Views',
            'Conversion Rate'
        ],
        'Value': [
            '45,230',
            '18,920',
            '24,810',
            '1,500',
            '42%',
            '68%',
            '51%',
            '2m 34s',
            '127,450',
            '3.2%'
        ]
    }
    
    df = pd.DataFrame(data)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_content = csv_buffer.getvalue()
    
    return {
        'filename': 'Website_Analytics_Report.csv',
        'content': base64.b64encode(csv_content.encode()).decode(),
        'mime_type': 'text/csv'
    }

def generate_cybersecurity_file():
    """Generate password hashes for cybersecurity simulation"""
    # Common weak passwords and their MD5 hashes
    passwords = {
        'password123': '482c811da5d5b4bc6d497ffa98491e38',
        'admin': '21232f297a57a5a743894a0e4a801fc3',
        'letmein': 'b7a875fc1ea228b9061041b7cec4bd3c',
        'qwerty': 'd8578edf8458ce06fbc5bb76a58c5ca4',
        '123456': 'e10adc3949ba59abbe56e057f20f883e'
    }
    
    content = "# Password Hash Cracking Challenge\n"
    content += "# Find the original passwords for these MD5 hashes\n\n"
    content += "Hash List:\n"
    for pwd, hash_val in passwords.items():
        content += f"{hash_val}\n"
    
    content += "\n# Common Password Wordlist:\n"
    wordlist = ['password', 'admin', 'letmein', 'qwerty', '123456', 'password123', 
                'welcome', 'monkey', 'dragon', 'master', 'github', 'login']
    content += "\n".join(wordlist)
    
    return {
        'filename': 'password_hashes.txt',
        'content': base64.b64encode(content.encode()).decode(),
        'mime_type': 'text/plain'
    }

def generate_paralegal_file():
    """Generate a contract for paralegal simulation"""
    contract = """
SOFTWARE LICENSE AGREEMENT

This Software License Agreement ("Agreement") is entered into on December 15, 2024,
between TechFlow Solutions Inc., a Delaware corporation ("Licensor"), and 
DataVantage Systems LLC, a California limited liability company ("Licensee").

WHEREAS, Licensor has developed proprietary software known as "Analytics Pro Suite"; and
WHEREAS, Licensee desires to obtain a license to use said software;

NOW, THEREFORE, the parties agree as follows:

1. GRANT OF LICENSE
Licensor hereby grants to Licensee a non-exclusive, non-transferable license to use
the Analytics Pro Suite software for internal business purposes only.

2. TERM
This Agreement shall commence on January 1, 2025, and continue for a period of
three (3) years, unless terminated earlier in accordance with the terms herein.

3. LICENSE FEE
Licensee agrees to pay Licensor an annual license fee of $45,000, payable in quarterly
installments of $11,250.

4. RESTRICTIONS
Licensee shall not: (a) modify, adapt, or create derivative works of the software;
(b) reverse engineer, decompile, or disassemble the software; or (c) distribute,
sublicense, or transfer the software to any third party.

5. CONFIDENTIALITY
Both parties acknowledge that they may have access to confidential information and
agree to maintain such information in strict confidence.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.

LICENSOR:                           LICENSEE:
TechFlow Solutions Inc.             DataVantage Systems LLC

By: /s/ Sarah Mitchell             By: /s/ Robert Chen
Name: Sarah Mitchell               Name: Robert Chen  
Title: Chief Executive Officer     Title: Chief Technology Officer
Date: December 15, 2024           Date: December 15, 2024
"""
    
    return {
        'filename': 'Software_License_Agreement.pdf',
        'content': base64.b64encode(contract.encode()).decode(),
        'mime_type': 'application/pdf'
    }

def generate_data_science_file():
    """Generate dataset for data science simulation"""
    # Customer satisfaction survey data
    data = {
        'Customer_ID': [f'CUST_{i:04d}' for i in range(1, 101)],
        'Age': [random.randint(22, 65) for _ in range(100)],
        'Satisfaction_Score': [random.randint(1, 10) for _ in range(100)],
        'Monthly_Spend': [random.randint(50, 500) for _ in range(100)],
        'Support_Calls': [random.randint(0, 8) for _ in range(100)],
        'Product_Category': [random.choice(['Premium', 'Standard', 'Basic']) for _ in range(100)]
    }
    
    # Ensure specific correlation for the task
    df = pd.DataFrame(data)
    # Set specific values to make correlation more obvious
    df.loc[df['Support_Calls'] > 5, 'Satisfaction_Score'] = random.randint(1, 4)
    correlation = df['Support_Calls'].corr(df['Satisfaction_Score'])
    
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, sheet_name='Customer_Data')
    excel_buffer.seek(0)
    
    return {
        'filename': 'Customer_Satisfaction_Dataset.xlsx',
        'content': base64.b64encode(excel_buffer.getvalue()).decode(),
        'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }

def generate_ux_design_file():
    """Generate user research report for UX design simulation"""
    report = """
USER RESEARCH FINDINGS REPORT
E-Commerce Mobile App Usability Study

STUDY OVERVIEW
Conducted: November 2024
Participants: 24 users (ages 25-45)
Method: Remote usability testing
Duration: 45 minutes per session

KEY FINDINGS:

1. CHECKOUT PROCESS ISSUES
- 78% of users abandoned cart during checkout
- Average time to complete purchase: 8.5 minutes (industry benchmark: 3-4 minutes)
- Main friction points: Too many form fields, unclear shipping options

2. NAVIGATION PROBLEMS  
- Users took average 2.3 minutes to find product search
- 65% couldn't locate account settings
- Category navigation described as "confusing" by 19/24 users

3. POSITIVE FEEDBACK
- Product images rated 8.2/10 for quality
- Loading speeds were satisfactory (avg 2.1 seconds)
- Users appreciated the wishlist functionality

4. PRIORITY RECOMMENDATIONS
A. Simplify checkout to 2-step process
B. Add prominent search bar to homepage  
C. Redesign main navigation menu
D. Implement guest checkout option

IMPACT ANALYSIS:
Implementing these changes could potentially reduce cart abandonment from 78% to an estimated 35-40%, based on industry standards.

Next Steps: Create wireframes addressing navigation and checkout flow issues.
"""
    
    return {
        'filename': 'UX_Research_Report.pdf',
        'content': base64.b64encode(report.encode()).decode(),
        'mime_type': 'application/pdf'
    }

def generate_content_marketing_file():
    """Generate content performance data for content marketing simulation"""
    data = {
        'Content_Type': ['Blog Post', 'Video', 'Infographic', 'Podcast', 'Webinar', 'Case Study', 'Ebook', 'Social Media'],
        'Views': [12450, 8920, 6730, 3200, 1850, 4560, 2340, 18750],
        'Engagement_Rate': ['4.2%', '7.8%', '3.1%', '12.5%', '15.3%', '6.7%', '8.9%', '2.4%'],
        'Conversion_Rate': ['2.1%', '3.4%', '1.8%', '8.2%', '11.7%', '4.5%', '6.3%', '0.8%'],
        'Production_Cost': [250, 1200, 400, 800, 2000, 600, 1500, 100],
        'Lead_Generation': [26, 30, 12, 26, 22, 21, 15, 15]
    }
    
    df = pd.DataFrame(data)
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, sheet_name='Content_Performance')
    excel_buffer.seek(0)
    
    return {
        'filename': 'Content_Performance_Analysis.xlsx',
        'content': base64.b64encode(excel_buffer.getvalue()).decode(),
        'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }

def generate_financial_analysis_file():
    """Generate financial data for investment analysis"""
    data = {
        'Company': ['TechCorp Inc', 'GreenEnergy Ltd', 'RetailMax Co', 'HealthPlus Inc', 'AutoDrive Co'],
        'Stock_Price': [125.50, 87.20, 45.75, 156.80, 92.10],
        'Market_Cap_B': [15.2, 8.7, 12.3, 18.9, 11.4],
        'PE_Ratio': [18.5, 22.3, 15.7, 28.2, 16.9],
        'Revenue_Growth': ['12.5%', '8.3%', '6.7%', '15.2%', '9.8%'],
        'Debt_to_Equity': [0.45, 0.32, 0.67, 0.28, 0.58],
        'ROE': ['14.2%', '11.8%', '9.3%', '16.7%', '12.1%'],
        'Dividend_Yield': ['2.1%', '3.4%', '4.2%', '1.8%', '2.9%'],
        'Risk_Rating': ['Medium', 'Low', 'High', 'Medium', 'Medium']
    }
    
    df = pd.DataFrame(data)
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, sheet_name='Investment_Analysis')
    excel_buffer.seek(0)
    
    return {
        'filename': 'Investment_Portfolio_Analysis.xlsx',
        'content': base64.b64encode(excel_buffer.getvalue()).decode(),
        'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }

def generate_hr_recruiting_file():
    """Generate candidate profiles for HR simulation"""
    candidates = """
CANDIDATE EVALUATION REPORT
Software Engineer Position - Senior Level

CANDIDATE A: Sarah Johnson
Experience: 6 years
Technical Skills: Python, React, AWS, Docker
Previous Companies: Google, Microsoft
Education: MS Computer Science, Stanford
Salary Expectation: $145K
Interview Score: 8.5/10
Strengths: Strong problem-solving, excellent communication
Concerns: May be overqualified, potential flight risk
Cultural Fit: High - collaborative, mentor-oriented

CANDIDATE B: Marcus Chen  
Experience: 4 years
Technical Skills: Java, Angular, Kubernetes, GraphQL
Previous Companies: Uber, Stripe
Education: BS Computer Science, UC Berkeley
Salary Expectation: $125K
Interview Score: 7.8/10
Strengths: Fast learner, startup experience
Concerns: Limited Python experience
Cultural Fit: High - innovative, results-driven

CANDIDATE C: Emily Rodriguez
Experience: 8 years
Technical Skills: Java, Python, Microservices, Jenkins
Previous Companies: Amazon, Salesforce
Education: BS Computer Engineering, MIT
Salary Expectation: $165K
Interview Score: 9.2/10
Strengths: Leadership experience, technical depth
Concerns: Above budget, may expect management role
Cultural Fit: Medium - more independent work style

EVALUATION CRITERIA:
- Technical competency (40%)
- Cultural alignment (25%) 
- Experience relevance (20%)
- Cost consideration (15%)

Which candidate represents the best overall value for a senior software engineer role?
"""
    
    return {
        'filename': 'Candidate_Evaluation_Report.pdf',
        'content': base64.b64encode(candidates.encode()).decode(),
        'mime_type': 'application/pdf'
    }

def generate_software_dev_file():
    """Generate code with bugs for software development simulation"""
    code = """
# E-Commerce Shopping Cart Bug Fix Challenge
# The following Python code has several bugs that are causing issues in production

class ShoppingCart:
    def __init__(self):
        self.items = []
        self.discount = 0
        
    def add_item(self, name, price, quantity):
        item = {
            'name': name,
            'price': price,
            'quantity': quantity
        }
        self.items.append(item)
        
    def remove_item(self, name):
        for item in self.items:
            if item['name'] = name:  # BUG 1: Assignment instead of comparison
                self.items.remove(item)
                break
                
    def calculate_total(self):
        total = 0
        for item in self.items:
            total += item['price'] * item['quantity']
        
        # Apply discount
        if self.discount > 0:
            total = total - (total * self.discount / 100)
            
        return total
        
    def apply_discount(self, discount_percent):
        if discount_percent > 100:  # BUG 2: Should also check if negative
            self.discount = 0
        else:
            self.discount = discount_percent
            
    def get_item_count(self):
        count = 0
        for item in self.items:
            count += item['quantity']
        return count
        
    def checkout(self):
        if len(self.items) == 0:
            return "Cart is empty"
        
        total = self.calculate_total()
        # BUG 3: No validation for minimum order amount
        return f"Order total: ${total:.2f}"

# Test the shopping cart
cart = ShoppingCart()
cart.add_item("Laptop", 999.99, 1)
cart.add_item("Mouse", 29.99, 2)
cart.apply_discount(10)

print(f"Items in cart: {cart.get_item_count()}")
print(f"Total: {cart.checkout()}")

# Find and list all the bugs in the code above
"""
    
    return {
        'filename': 'shopping_cart_debug.py',
        'content': base64.b64encode(code.encode()).decode(),
        'mime_type': 'text/x-python-script'
    }

def generate_api_requirements_file():
    """Generate API requirements for development simulation"""
    requirements = """
API Authentication Endpoint Requirements

ENDPOINT: POST /api/auth/login

REQUIREMENTS:
1. Accept JSON payload with 'email' and 'password' fields
2. Validate email format (must contain @ and valid domain)
3. Validate password (minimum 8 characters, at least one letter and one number)
4. Check credentials against user database
5. Return appropriate HTTP status codes:
   - 200: Successful login
   - 400: Invalid input format
   - 401: Invalid credentials
   - 422: Validation errors

RESPONSE FORMAT:
Success (200):
{
  "access_token": "jwt_token_here",
  "token_type": "bearer",
  "user": {
    "id": "user_id",
    "email": "user@example.com"
  }
}

Error (400/401/422):
{
  "detail": "Error message",
  "error_code": "ERROR_CODE"
}

SECURITY REQUIREMENTS:
- Hash passwords using bcrypt
- Generate JWT tokens with 24-hour expiration
- Include rate limiting (max 5 attempts per minute)
- Log all authentication attempts

IMPLEMENTATION NOTES:
- Use FastAPI with Pydantic for validation
- Store user data in MongoDB
- Implement proper error handling
- Add input sanitization

What HTTP status code should be returned for successful login?
"""
    
    return {
        'filename': 'api_requirements.txt',
        'content': base64.b64encode(requirements.encode()).decode(),
        'mime_type': 'text/plain'
    }

def generate_calculator_class_file():
    """Generate calculator class for testing simulation"""
    code = """
class Calculator:
    def __init__(self):
        self.history = []
    
    def add(self, a, b):
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
    
    def subtract(self, a, b):
        result = a - b
        self.history.append(f"{a} - {b} = {result}")
        return result
    
    def multiply(self, a, b):
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result
    
    def divide(self, a, b):
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
        self.history.append(f"{a} / {b} = {result}")
        return result
    
    def power(self, a, b):
        result = a ** b
        self.history.append(f"{a} ^ {b} = {result}")
        return result
    
    def square_root(self, a):
        if a < 0:
            raise ValueError("Cannot calculate square root of negative number")
        result = a ** 0.5
        self.history.append(f"√{a} = {result}")
        return result
    
    def get_history(self):
        return self.history
    
    def clear_history(self):
        self.history = []

# Test cases to verify:
# 1. Basic arithmetic operations
# 2. Division by zero handling
# 3. Square root of negative numbers
# 4. History tracking
# 5. Edge cases (very large numbers, decimals)
# 6. Input validation
# 7. Memory management

How many test cases would you write to thoroughly test this calculator class?
"""
    
    return {
        'filename': 'calculator_class.py',
        'content': base64.b64encode(code.encode()).decode(),
        'mime_type': 'text/x-python-script'
    }

def generate_network_config_file():
    """Generate network configuration for penetration testing"""
    config = """
NETWORK CONFIGURATION ANALYSIS

Router Configuration:
- Model: Cisco ASR 1000
- Firmware: 15.1(4)M12a
- Default admin credentials: admin/admin123
- SSH enabled on port 22
- Telnet enabled on port 23
- HTTP management on port 80 (no HTTPS)

Firewall Rules:
- Allow all traffic from 192.168.1.0/24
- Allow SSH from 10.0.0.0/8
- Block ICMP from external networks
- Allow HTTP/HTTPS from anywhere
- Allow FTP on port 21

Server Configuration:
- Web Server: Apache 2.4.41 on Ubuntu 18.04
- Database: MySQL 5.7 with root password 'password'
- File permissions: 777 on /var/www/html
- Log files: /var/log/apache2/access.log (world readable)

Network Topology:
- DMZ: 192.168.1.0/24
- Internal: 10.0.0.0/8
- External: Public IP range
- VPN: OpenVPN with weak encryption (DES)

Security Issues Found:
1. Default credentials on router
2. Unencrypted management interface
3. Weak database password
4. Overly permissive file permissions
5. Weak VPN encryption
6. Telnet enabled (unencrypted)
7. No intrusion detection system

What is the most critical security vulnerability in this configuration?
"""
    
    return {
        'filename': 'network_config.txt',
        'content': base64.b64encode(config.encode()).decode(),
        'mime_type': 'text/plain'
    }

def generate_customer_churn_file():
    """Generate customer churn dataset for data science analysis"""
    data = {
        'Customer_ID': [f'CUST_{i:04d}' for i in range(1, 1001)],
        'Age': [random.randint(18, 80) for _ in range(1000)],
        'Monthly_Charges': [round(random.uniform(20, 120), 2) for _ in range(1000)],
        'Tenure_Months': [random.randint(1, 72) for _ in range(1000)],
        'Contract_Type': [random.choice(['Month-to-month', 'One year', 'Two year']) for _ in range(1000)],
        'Internet_Service': [random.choice(['DSL', 'Fiber optic', 'No']) for _ in range(1000)],
        'Online_Security': [random.choice(['Yes', 'No', 'No internet service']) for _ in range(1000)],
        'Tech_Support': [random.choice(['Yes', 'No', 'No internet service']) for _ in range(1000)],
        'Payment_Method': [random.choice(['Electronic check', 'Mailed check', 'Bank transfer', 'Credit card']) for _ in range(1000)],
        'Churn': [random.choice(['Yes', 'No']) for _ in range(1000)]
    }
    
    # Add some correlation between features and churn
    df = pd.DataFrame(data)
    # Higher monthly charges correlate with churn
    df.loc[df['Monthly_Charges'] > 80, 'Churn'] = 'Yes'
    # Month-to-month contracts have higher churn
    df.loc[df['Contract_Type'] == 'Month-to-month', 'Churn'] = 'Yes'
    # No online security correlates with churn
    df.loc[df['Online_Security'] == 'No', 'Churn'] = 'Yes'
    
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, sheet_name='Customer_Churn_Data')
    excel_buffer.seek(0)
    
    return {
        'filename': 'customer_churn_dataset.xlsx',
        'content': base64.b64encode(excel_buffer.getvalue()).decode(),
        'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }

def generate_email_dataset_file():
    """Generate email dataset for ML classification"""
    emails = [
        "Get rich quick! Make $1000 per day working from home!",
        "Your account has been suspended. Click here to verify your identity.",
        "Meeting reminder: Project review at 3 PM today",
        "Congratulations! You've won $50,000 in our lottery!",
        "Please review the attached quarterly report",
        "URGENT: Your bank account will be closed in 24 hours",
        "Team lunch tomorrow at 12 PM in the cafeteria",
        "Free Viagra! Order now and save 90%!",
        "Code review completed. Please merge the changes.",
        "You have 3 new messages in your inbox"
    ]
    
    labels = ['spam', 'spam', 'ham', 'spam', 'ham', 'spam', 'ham', 'spam', 'ham', 'ham']
    
    data = {
        'email_text': emails * 100,  # Repeat to create larger dataset
        'label': labels * 100
    }
    
    df = pd.DataFrame(data)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_content = csv_buffer.getvalue()
    
    return {
        'filename': 'email_classification_dataset.csv',
        'content': base64.b64encode(csv_content.encode()).decode(),
        'mime_type': 'text/csv'
    }

def generate_webapp_code_file():
    """Generate web application code for Docker containerization"""
    code = """
# Flask Web Application
from flask import Flask, render_template, request, jsonify
import os
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/health')
def health_check():
    return jsonify({"status": "healthy", "version": "1.0.0"})

@app.route('/api/users', methods=['GET'])
def get_users():
    # Simulate database query
    users = [
        {"id": 1, "name": "John Doe", "email": "john@example.com"},
        {"id": 2, "name": "Jane Smith", "email": "jane@example.com"}
    ]
    return jsonify(users)

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    if not data or 'name' not in data or 'email' not in data:
        return jsonify({"error": "Name and email are required"}), 400
    
    # Simulate user creation
    new_user = {
        "id": 3,
        "name": data['name'],
        "email": data['email']
    }
    return jsonify(new_user), 201

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
"""
    
    return {
        'filename': 'app.py',
        'content': base64.b64encode(code.encode()).decode(),
        'mime_type': 'text/x-python-script'
    }

def generate_app_config_file():
    """Generate application configuration for monitoring setup"""
    config = """
APPLICATION MONITORING CONFIGURATION

Application: E-commerce Web Service
Environment: Production
Expected Load: 1000 requests/minute
Critical Thresholds:
- Response time: < 200ms
- Error rate: < 1%
- CPU usage: < 80%
- Memory usage: < 85%
- Disk usage: < 90%

Monitoring Requirements:
1. Real-time dashboards
2. Alert notifications (email, Slack)
3. Log aggregation and analysis
4. Performance metrics tracking
5. Error tracking and reporting
6. Uptime monitoring
7. Database performance monitoring

Alert Conditions:
- High response time (> 500ms for 5 minutes)
- High error rate (> 5% for 2 minutes)
- High resource usage (> 90% for 10 minutes)
- Service down (no response for 1 minute)
- Database connection failures
- Memory leaks detected

Tools to Configure:
- Prometheus for metrics collection
- Grafana for visualization
- AlertManager for notifications
- ELK Stack for log analysis
- New Relic for APM

How many monitoring rules would you create for this application?
"""
    
    return {
        'filename': 'monitoring_requirements.txt',
        'content': base64.b64encode(config.encode()).decode(),
        'mime_type': 'text/plain'
    }

def generate_aws_requirements_file():
    """Generate AWS infrastructure requirements"""
    requirements = """
AWS INFRASTRUCTURE REQUIREMENTS

Application: Multi-tier Web Application
Expected Users: 10,000 concurrent
Data Storage: 1TB initially, growing 20% monthly
Availability: 99.9% uptime requirement
Budget: $5,000/month maximum

Requirements:
1. Web Tier: Handle HTTP requests, serve static content
2. Application Tier: Process business logic, API endpoints
3. Database Tier: Store user data, transactions, analytics
4. CDN: Global content delivery
5. Load Balancing: Distribute traffic across instances
6. Auto Scaling: Handle traffic spikes
7. Security: VPC, security groups, IAM
8. Monitoring: CloudWatch, logging, alerting
9. Backup: Automated backups, disaster recovery
10. CI/CD: Code deployment pipeline

Performance Requirements:
- Response time: < 100ms
- Throughput: 10,000 requests/second
- Storage: 1TB with 99.999999999% durability
- Backup: Daily automated backups
- Recovery: RTO < 4 hours, RPO < 1 hour

Security Requirements:
- HTTPS only
- VPC with private subnets
- WAF protection
- DDoS protection
- Encryption at rest and in transit
- IAM roles with least privilege

How many AWS services would you use to build this infrastructure?
"""
    
    return {
        'filename': 'aws_requirements.txt',
        'content': base64.b64encode(requirements.encode()).decode(),
        'mime_type': 'text/plain'
    }

def generate_security_requirements_file():
    """Generate security requirements for cloud configuration"""
    requirements = """
CLOUD SECURITY CONFIGURATION REQUIREMENTS

Environment: Multi-account AWS setup
Compliance: SOC 2, GDPR, HIPAA
Data Classification: PII, Financial, Health records

Security Controls Required:
1. Identity and Access Management (IAM)
   - MFA for all users
   - Role-based access control
   - Regular access reviews
   - Service accounts with limited permissions

2. Network Security
   - VPC with public/private subnets
   - Security groups (restrictive rules)
   - NACLs for additional layer
   - VPN for secure access

3. Data Protection
   - Encryption at rest (AES-256)
   - Encryption in transit (TLS 1.3)
   - Key management (AWS KMS)
   - Data classification and tagging

4. Monitoring and Logging
   - CloudTrail for API logging
   - CloudWatch for metrics
   - GuardDuty for threat detection
   - Config for compliance monitoring

5. Incident Response
   - Automated response playbooks
   - Security incident escalation
   - Forensic data collection
   - Communication protocols

How many security groups would you create for this multi-tier architecture?
"""
    
    return {
        'filename': 'security_requirements.txt',
        'content': base64.b64encode(requirements.encode()).decode(),
        'mime_type': 'text/plain'
    }

def generate_ios_app_file():
    """Generate iOS app code for performance optimization"""
    code = """
// iOS App Performance Issues
import UIKit
import Foundation

class ViewController: UIViewController {
    @IBOutlet weak var tableView: UITableView!
    @IBOutlet weak var imageView: UIImageView!
    
    var dataArray: [String] = []
    var images: [UIImage] = []
    
    override func viewDidLoad() {
        super.viewDidLoad()
        setupTableView()
        loadData()
        loadImages()
    }
    
    func setupTableView() {
        tableView.delegate = self
        tableView.dataSource = self
        // ISSUE 1: No cell reuse identifier
        tableView.register(UITableViewCell.self, forCellReuseIdentifier: "Cell")
    }
    
    func loadData() {
        // ISSUE 2: Loading data on main thread
        for i in 0..<10000 {
            dataArray.append("Item \\(i)")
        }
        tableView.reloadData()
    }
    
    func loadImages() {
        // ISSUE 3: Loading large images synchronously
        for i in 0..<100 {
            if let image = UIImage(named: "large_image_\\(i).jpg") {
                images.append(image)
            }
        }
    }
    
    func processData() {
        // ISSUE 4: Heavy computation on main thread
        var result = 0
        for i in 0..<1000000 {
            result += i * i
        }
        print("Result: \\(result)")
    }
    
    @IBAction func buttonTapped(_ sender: UIButton) {
        // ISSUE 5: No memory management
        let largeArray = Array(0..<1000000)
        processData()
    }
}

extension ViewController: UITableViewDataSource, UITableViewDelegate {
    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        return dataArray.count
    }
    
    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        // ISSUE 6: Creating new cell every time
        let cell = UITableViewCell(style: .default, reuseIdentifier: "Cell")
        cell.textLabel?.text = dataArray[indexPath.row]
        
        // ISSUE 7: Setting image without optimization
        if indexPath.row < images.count {
            cell.imageView?.image = images[indexPath.row]
        }
        
        return cell
    }
}

// ISSUE 8: No proper memory management
class DataManager {
    var cache: [String: Any] = [:]
    
    func storeData(_ data: Any, forKey key: String) {
        cache[key] = data
        // No cache size limit or cleanup
    }
}

How many performance issues can you identify in this iOS app code?
"""
    
    return {
        'filename': 'ios_app_code.swift',
        'content': base64.b64encode(code.encode()).decode(),
        'mime_type': 'text/x-swift'
    }

def generate_react_native_file():
    """Generate React Native code for state management"""
    code = """
// React Native App with State Management Issues
import React, { useState, useEffect } from 'react';
import { View, Text, Button, FlatList, StyleSheet } from 'react-native';

const App = () => {
  // ISSUE 1: Multiple useState hooks for related state
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [userCount, setUserCount] = useState(0);
  const [filter, setFilter] = useState('');
  const [sortBy, setSortBy] = useState('name');

  // ISSUE 2: No proper state management structure
  const [appState, setAppState] = useState({
    users: [],
    loading: false,
    error: null,
    selectedUser: null,
    userCount: 0,
    filter: '',
    sortBy: 'name'
  });

  useEffect(() => {
    // ISSUE 3: No cleanup for async operations
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const response = await fetch('https://api.example.com/users');
      const data = await response.json();
      setUsers(data);
      setUserCount(data.length);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const addUser = (user) => {
    // ISSUE 4: Direct state mutation
    users.push(user);
    setUsers(users);
    setUserCount(users.length);
  };

  const updateUser = (id, updates) => {
    // ISSUE 5: Inefficient state update
    const updatedUsers = users.map(user => 
      user.id === id ? { ...user, ...updates } : user
    );
    setUsers(updatedUsers);
  };

  const deleteUser = (id) => {
    // ISSUE 6: No optimistic updates
    fetch(`https://api.example.com/users/${id}`, { method: 'DELETE' })
      .then(() => {
        setUsers(users.filter(user => user.id !== id));
        setUserCount(users.length - 1);
      });
  };

  const filteredUsers = users.filter(user => 
    user.name.toLowerCase().includes(filter.toLowerCase())
  );

  const sortedUsers = filteredUsers.sort((a, b) => 
    a[sortBy] > b[sortBy] ? 1 : -1
  );

  return (
    <View style={styles.container}>
      <Text>Users: {userCount}</Text>
      {loading && <Text>Loading...</Text>}
      {error && <Text>Error: {error}</Text>}
      
      <FlatList
        data={sortedUsers}
        keyExtractor={(item) => item.id.toString()}
        renderItem={({ item }) => (
          <View style={styles.userItem}>
            <Text>{item.name}</Text>
            <Button title="Edit" onPress={() => updateUser(item.id, { name: 'Updated' })} />
            <Button title="Delete" onPress={() => deleteUser(item.id)} />
          </View>
        )}
      />
    </View>
  );
};

// ISSUE 7: No proper state management solution
// Should use Redux, Context API, or Zustand

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
  },
  userItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 10,
    borderBottomWidth: 1,
  },
});

export default App;

// How many reducers would you create for proper state management?
"""
    
    return {
        'filename': 'react_native_app.js',
        'content': base64.b64encode(code.encode()).decode(),
        'mime_type': 'text/javascript'
    }

def generate_product_roadmap_file():
    """Generate product roadmap data for PM strategy simulation"""
    data = {
        'Feature': [
            'User Authentication',
            'Dashboard Analytics',
            'Mobile App',
            'API Integration',
            'Push Notifications',
            'Advanced Search',
            'Team Collaboration',
            'Data Export',
            'Custom Themes',
            'Real-time Chat'
        ],
        'User_Demand': [95, 87, 92, 78, 65, 82, 88, 71, 45, 73],
        'Business_Impact': [90, 85, 80, 70, 60, 75, 85, 65, 40, 70],
        'Development_Effort': [3, 5, 8, 4, 2, 6, 7, 3, 2, 5],
        'Revenue_Impact': [85, 80, 75, 65, 55, 70, 80, 60, 35, 65],
        'RICE_Score': [28.3, 14.8, 9.2, 13.6, 21.7, 10.2, 10.6, 19.3, 15.8, 9.5]
    }
    
    df = pd.DataFrame(data)
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, sheet_name='Product_Features')
    excel_buffer.seek(0)
    
    return {
        'filename': 'product_roadmap_data.xlsx',
        'content': base64.b64encode(excel_buffer.getvalue()).decode(),
        'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }

def generate_product_metrics_file():
    """Generate product metrics for PM analytics simulation"""
    data = {
        'Metric': [
            'Monthly Active Users',
            'Daily Active Users',
            'User Retention (7-day)',
            'User Retention (30-day)',
            'Conversion Rate',
            'Average Session Duration',
            'Bounce Rate',
            'Feature Adoption Rate',
            'Customer Satisfaction Score',
            'Churn Rate'
        ],
        'Current_Value': [12500, 4200, '68%', '45%', '12.5%', '8m 32s', '35%', '23%', '4.2/5', '8%'],
        'Previous_Month': [11800, 3900, '65%', '42%', '11.8%', '7m 45s', '38%', '21%', '4.0/5', '9%'],
        'Target': [15000, 5000, '75%', '50%', '15%', '10m', '30%', '30%', '4.5/5', '5%'],
        'Trend': ['↗️', '↗️', '↗️', '↗️', '↗️', '↗️', '↘️', '↗️', '↗️', '↘️']
    }
    
    df = pd.DataFrame(data)
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, sheet_name='Product_Metrics')
    excel_buffer.seek(0)
    
    return {
        'filename': 'product_metrics_dashboard.xlsx',
        'content': base64.b64encode(excel_buffer.getvalue()).decode(),
        'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }

def generate_user_interviews_file():
    """Generate user interview data for PM research simulation"""
    interviews = """
USER INTERVIEW ANALYSIS - MOBILE APP FEEDBACK
Conducted: December 2024 | Participants: 20 users | Duration: 30-45 minutes each

INTERVIEW SUMMARIES:

User 1 (Sarah, 28, Marketing Manager):
"I love the app's design, but it's really slow to load. Sometimes I have to wait 10-15 seconds just to see my dashboard. The search function is also not very intuitive."

User 2 (Mike, 35, Sales Director):
"The slow loading is killing my productivity. I use this app 20+ times a day and the delays add up. Also, the notifications don't work properly on my phone."

User 3 (Lisa, 42, Operations Manager):
"Great features, terrible performance. The app crashes at least once a day, usually when I'm trying to upload files. The slow loading is the worst part though."

User 4 (David, 31, Project Manager):
"Slow loading times are frustrating. The interface is clean but I wish there was a dark mode. Also, the search could be better - it doesn't find things I know are there."

User 5 (Emma, 26, Content Creator):
"The app is beautiful but so slow! It takes forever to load images and videos. I also wish there was better organization for my content."

User 6 (James, 38, Finance Manager):
"Performance issues are my main concern. The slow loading affects my work flow. The reporting features are good but need to be faster."

User 7 (Anna, 29, HR Specialist):
"Love the functionality but hate the wait times. Slow loading is the biggest issue. Also, the mobile version needs work - it's not as responsive as the web version."

User 8 (Tom, 33, IT Manager):
"Technical issues: slow loading, occasional crashes, and the API seems unreliable. The core features work but performance needs improvement."

User 9 (Rachel, 27, Designer):
"Slow loading is my biggest pain point. The app has great potential but the performance issues make it hard to use daily. Also, the file upload is unreliable."

User 10 (Chris, 40, CEO):
"Slow loading times are affecting team productivity. We need faster performance and more reliable file handling. The concept is great but execution needs work."

User 11 (Maria, 32, Account Manager):
"Performance is the main issue - slow loading and crashes. The interface is nice but I need it to work faster. Also, better search functionality would help."

User 12 (John, 36, Developer):
"Slow loading is the primary concern. The app architecture seems solid but there are performance bottlenecks. Also, the mobile experience needs optimization."

User 13 (Sarah, 30, Marketing Coordinator):
"Love the features but hate the wait times. Slow loading is the biggest frustration. The design is great but performance needs to match."

User 14 (Mike, 34, Sales Manager):
"Slow loading is killing my efficiency. I use this app constantly and the delays are unacceptable. Also, the notifications are inconsistent."

User 15 (Lisa, 41, Operations Director):
"Performance issues are my main concern. Slow loading affects my daily workflow. The app has potential but needs to be faster and more reliable."

User 16 (David, 29, Project Coordinator):
"Slow loading times are frustrating. The interface is good but performance needs improvement. Also, better file organization would help."

User 17 (Emma, 25, Content Manager):
"The app is visually appealing but so slow! Loading times are terrible. I also need better content management features."

User 18 (James, 37, Finance Director):
"Slow loading is my biggest issue. It affects my productivity daily. The reporting is good but needs to be faster and more responsive."

User 19 (Anna, 28, HR Manager):
"Performance is the main problem - slow loading and occasional crashes. The functionality is there but execution needs work."

User 20 (Tom, 35, IT Director):
"Slow loading is the primary technical issue. The app has good features but performance bottlenecks are affecting user experience."

KEY THEMES IDENTIFIED:
1. Slow loading times (mentioned 18/20 times)
2. Performance issues (mentioned 15/20 times)
3. Mobile optimization (mentioned 8/20 times)
4. Search functionality (mentioned 6/20 times)
5. File upload reliability (mentioned 5/20 times)
6. Notification issues (mentioned 4/20 times)
7. Dark mode request (mentioned 3/20 times)

What is the most frequently mentioned pain point?
"""
    
    return {
        'filename': 'user_interview_analysis.txt',
        'content': base64.b64encode(interviews.encode()).decode(),
        'mime_type': 'text/plain'
    }

# Authentication Routes
@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password
    )
    
    await db.users.insert_one(user.dict())
    
    # Create token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["id"]}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.get("/auth/me", response_model=UserProfile)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        skill_badges=current_user.skill_badges,
        completed_simulations=current_user.completed_simulations,
        created_at=current_user.created_at
    )

# Tech Field Routes
@api_router.get("/tech-fields", response_model=List[TechField])
async def get_tech_fields():
    fields = await db.tech_fields.find().to_list(1000)
    return [TechField(**field) for field in fields]

@api_router.get("/tech-fields/{field_id}/simulations", response_model=List[SimulationPublic])
async def get_simulations_by_field(field_id: str):
    simulations = await db.simulations.find({"field_id": field_id}).to_list(1000)
    return [SimulationPublic(**_strip_correct_answers(sim)) for sim in simulations]

# Simulation Routes
@api_router.get("/simulations", response_model=List[SimulationPublic])
async def get_simulations():
    simulations = await db.simulations.find().to_list(1000)
    return [SimulationPublic(**_strip_correct_answers(sim)) for sim in simulations]

@api_router.get("/simulations/{simulation_id}", response_model=SimulationPublic)
async def get_simulation(simulation_id: str):
    simulation = await db.simulations.find_one({"id": simulation_id})
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return SimulationPublic(**_strip_correct_answers(simulation))


def _strip_correct_answers(simulation_doc: Dict[str, Any]) -> Dict[str, Any]:
    sim = dict(simulation_doc)
    # Convert questions to public without correct_answer
    if sim.get("questions"):
        sim["questions"] = [
            {
                "id": q.get("id"),
                "prompt": q.get("prompt"),
                "expected_answer_type": q.get("expected_answer_type"),
                "hints": q.get("hints", []),
                # Provide masked UI hints: length and mask based on normalized expected answer
                "answer_mask": ("*" * len(str(q.get("correct_answer", "")).replace("_", " "))) if q.get("correct_answer") else None,
                "max_length": len(str(q.get("correct_answer", "")).replace("_", " ")) if q.get("correct_answer") else None,
            }
            for q in sim["questions"]
        ]
    return sim

@api_router.get("/simulations/{simulation_id}/file", response_model=FileDownload)
async def get_simulation_file(simulation_id: str):
    """Generate and return the file for a specific simulation"""
    simulation = await db.simulations.find_one({"id": simulation_id})
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    file_generators = {
        # Software Engineering
        "se-debugging-1": generate_software_dev_file,
        "se-development-1": generate_api_requirements_file,
        "se-testing-1": generate_calculator_class_file,
        
        # Cybersecurity
        "cyber-password-1": generate_cybersecurity_file,
        "cyber-penetration-1": generate_network_config_file,
        
        # Data Science
        "ds-analysis-1": generate_customer_churn_file,
        "ds-modeling-1": generate_email_dataset_file,
        
        # DevOps
        "devops-deployment-1": generate_webapp_code_file,
        "devops-monitoring-1": generate_app_config_file,
        
        # Cloud Computing
        "cloud-aws-1": generate_aws_requirements_file,
        "cloud-security-1": generate_security_requirements_file,
        
        # Mobile Development
        "mobile-native-1": generate_ios_app_file,
        "mobile-cross-1": generate_react_native_file,
        
        # Product Management
        "pm-strategy-1": generate_product_roadmap_file,
        "pm-analytics-1": generate_product_metrics_file,
        "pm-user-research-1": generate_user_interviews_file
    }
    
    generator = file_generators.get(simulation_id)
    if not generator:
        raise HTTPException(status_code=404, detail="File not available for this simulation")
    
    return FileDownload(**generator())

@api_router.post("/simulations/submit", response_model=SimulationSubmission)
async def submit_simulation(
    payload: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user)
):
    # Backward/forward compatible payload extraction
    try:
        simulation_id: str = str(payload.get("simulation_id") or payload.get("id") or "").strip()
        if not simulation_id:
            raise HTTPException(status_code=422, detail="simulation_id is required")
        single_answer = payload.get("answer")
        answers_list = payload.get("answers")
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body")
    # Multi-question path
    if answers_list:
        simulation = await db.simulations.find_one({"id": simulation_id})
        if not simulation:
            raise HTTPException(status_code=404, detail="Simulation not found")
        # Build map of question_id -> correct_answer
        qmap = {q["id"]: q.get("correct_answer", "") for q in simulation.get("questions", [])}
        per_question = []
        all_correct = True
        for qa in answers_list:
            # Robust extraction
            qid = str(qa.get("question_id") or qa.get("id") or "").strip()
            ans = str(qa.get("answer") or "").strip()
            if not qid:
                all_correct = False
                per_question.append({
                    "question_id": qid or "",
                    "answer": ans,
                    "is_correct": False,
                    "feedback": "Missing question_id"
                })
                continue
            expected = qmap.get(qid)
            # If question not found, mark incorrect
            is_q_correct = False
            feedback_text = ""
            if expected is not None:
                # Determine expected type from simulation question metadata
                q_meta = next((q for q in simulation.get("questions", []) if q.get("id") == qid), None)
                expected_type = (q_meta.get("expected_answer_type") if q_meta else "text") or "text"
                user_clean = str(ans).strip().lower()
                correct_clean = str(expected).strip().lower()
                try:
                    # Normalize underscores to spaces for text comparison
                    if expected_type in ["text", "list"]:
                        user_norm = user_clean.replace('_', ' ').strip()
                        correct_norm = correct_clean.replace('_', ' ').strip()
                    else:
                        user_norm = user_clean
                        correct_norm = correct_clean
                    if expected_type in ["number", "percentage"]:
                        u = user_norm.replace('%', '').replace(' ', '')
                        c = correct_norm.replace('%', '').replace(' ', '')
                        is_q_correct = float(u) == float(c)
                    elif expected_type == "list":
                        user_list = [x.strip().lower() for x in user_norm.split(',') if x.strip()]
                        correct_list = [x.strip().lower() for x in correct_norm.split(',') if x.strip()]
                        is_q_correct = all(item in user_list for item in correct_list)
                    else:
                        is_q_correct = user_norm == correct_norm
                except Exception:
                    is_q_correct = user_clean.replace('_', ' ') == correct_clean.replace('_', ' ')
                feedback_text = ""
                # Per-question feedback overrides for richer guidance
                per_question_feedback = {
                    "se-debugging-1": {
                        "q1": {
                            "correct": "There are 5 critical logic issues impacting reliability.",
                            "incorrect": "Count distinct logic bugs across functions; check assignment vs comparison, input validation, concurrency, and empty cart checks."
                        },
                        "q2": {
                            "correct": "Negative discount validation is missing; values below 0 must be rejected.",
                            "incorrect": "Review discount handling: add validation to prevent negative or over-100% discounts."
                        }
                    },
                    "ds-analysis-1": {
                        "q1": {
                            "correct": "Spot on — Monthly_Charges shows the strongest positive correlation with churn.",
                            "incorrect": "Check correlations again — pricing-related features (e.g., Monthly_Charges) are highly predictive."
                        },
                        "q2": {
                            "correct": "Correct — churn is higher for month-to-month contracts versus fixed terms.",
                            "incorrect": "Compare churn rates across Contract_Type — month-to-month users churn more often."
                        },
                        "q3": {
                            "correct": "Yes — Online_Security (and similar add-ons) reduce churn likelihood.",
                            "incorrect": "Consider features that add security/support; they are associated with lower churn (e.g., Online_Security)."
                        }
                    },
                    "ds-modeling-1": {
                        "q1": {
                            "correct": "Great — hitting ~85% accuracy meets the target for this dataset.",
                            "incorrect": "Aim for around 85% accuracy; review preprocessing and model selection."
                        },
                        "q2": {
                            "correct": "Naive Bayes is a solid baseline for spam filtering.",
                            "incorrect": "Consider classic text classifiers like Naive Bayes for this task."
                        },
                        "q3": {
                            "correct": "TF-IDF is an appropriate feature extraction approach here.",
                            "incorrect": "Use a standard feature extraction method like TF-IDF for text."
                        }
                    }
                }
                sim_map = per_question_feedback.get(simulation_id, {})
                q_map = sim_map.get(qid)
                if q_map:
                    feedback_text = q_map["correct"] if is_q_correct else q_map["incorrect"]
            per_question.append({
                "question_id": qid,
                "answer": ans,
                "is_correct": is_q_correct,
                "feedback": feedback_text
            })
            if not is_q_correct:
                all_correct = False

        # Build overall AI feedback with clear rules:
        # - If all questions are correct, show a concise completion summary (do not repeat per-question feedback)
        # - Otherwise, join per-question feedback and add a fallback if still empty
        joined = "; ".join([p.get("feedback", "") for p in per_question if p.get("feedback")])
        if all_correct:
            ai_text = f"Excellent work! You completed '{simulation.get('title', 'this simulation')}' and answered all questions correctly."
        else:
            ai_text = joined or "Good effort! Review the guidance above for incorrect questions and try again."

        submission = SimulationSubmission(
            user_id=current_user.id,
            simulation_id=simulation_id,
            answer=json.dumps(per_question),
            ai_feedback=ai_text,
            is_correct=all_correct,
        )

        # Award badge only if all questions are correct
        if all_correct:
            badge_map = {
                # Software Engineering
                "se-debugging-1": "Debugging Specialist",
                "se-development-1": "API Development Expert",
                "se-testing-1": "Quality Assurance Professional",
                # Cybersecurity
                "cyber-password-1": "Security Analyst",
                "cyber-penetration-1": "Penetration Tester",
                # Data Science
                "ds-analysis-1": "Data Analyst",
                "ds-modeling-1": "Machine Learning Engineer",
                # DevOps
                "devops-deployment-1": "DevOps Engineer",
                "devops-monitoring-1": "Site Reliability Engineer",
                # Cloud Computing
                "cloud-aws-1": "Cloud Architect",
                "cloud-security-1": "Cloud Security Engineer",
                # Mobile Development
                "mobile-native-1": "iOS Developer",
                "mobile-cross-1": "React Native Developer",
                # Product Management
                "pm-strategy-1": "Product Strategist",
                "pm-analytics-1": "Product Analyst",
                "pm-user-research-1": "User Research Specialist",
            }
            badge = badge_map.get(simulation_id)
            if badge and badge not in current_user.skill_badges:
                submission.skill_badge_earned = badge
                await db.users.update_one(
                    {"id": current_user.id},
                    {"$addToSet": {"skill_badges": badge, "completed_simulations": simulation_id}},
                )

        await db.submissions.insert_one(submission.dict())
        return submission

    # end multi-question path

    # Correct answers mapping for tech simulations
    # Single-answer fallback path
    correct_answers = {
        # Software Engineering
        "se-debugging-1": "5",  # Number of bugs in shopping cart
        "se-development-1": "200",  # HTTP status code for successful login
        "se-testing-1": "7",  # Number of test cases for calculator
        
        # Cybersecurity
        "cyber-password-1": "password123,admin,letmein",  # Cracked passwords
        "cyber-penetration-1": "default_credentials",  # Most critical vulnerability
        
        # Data Science
        "ds-analysis-1": "Monthly_Charges",  # Strongest churn predictor
        "ds-modeling-1": "85%",  # ML model accuracy
        
        # DevOps
        "devops-deployment-1": "4",  # Docker layers
        "devops-monitoring-1": "6",  # Monitoring rules
        
        # Cloud Computing
        "cloud-aws-1": "12",  # AWS services needed
        "cloud-security-1": "5",  # Security groups
        
        # Mobile Development
        "mobile-native-1": "8",  # Performance issues in iOS code
        "mobile-cross-1": "3",  # Reducers for state management
        
        # Product Management
        "pm-strategy-1": "5",  # Features for Q1 roadmap
        "pm-analytics-1": "12.5%",  # Conversion rate
        "pm-user-research-1": "slow_loading"  # Most common pain point
    }
    
    # Skill badge mapping for tech simulations
    badge_map = {
        # Software Engineering
        "se-debugging-1": "Debugging Specialist",
        "se-development-1": "API Development Expert",
        "se-testing-1": "Quality Assurance Professional",
        
        # Cybersecurity
        "cyber-password-1": "Security Analyst",
        "cyber-penetration-1": "Penetration Tester",
        
        # Data Science
        "ds-analysis-1": "Data Analyst",
        "ds-modeling-1": "Machine Learning Engineer",
        
        # DevOps
        "devops-deployment-1": "DevOps Engineer",
        "devops-monitoring-1": "Site Reliability Engineer",
        
        # Cloud Computing
        "cloud-aws-1": "Cloud Architect",
        "cloud-security-1": "Cloud Security Engineer",
        
        # Mobile Development
        "mobile-native-1": "iOS Developer",
        "mobile-cross-1": "React Native Developer",
        
        # Product Management
        "pm-strategy-1": "Product Strategist",
        "pm-analytics-1": "Product Analyst",
        "pm-user-research-1": "User Research Specialist"
    }
    
    # Generate AI feedback
    correct_answer = correct_answers.get(simulation_id)
    feedback_result = await generate_ai_feedback(
        simulation_id,
        str(single_answer) if single_answer is not None else "",
        correct_answer
    )
    
    # Create submission
    submission = SimulationSubmission(
        user_id=current_user.id,
        simulation_id=simulation_id,
        answer=str(single_answer) if single_answer is not None else "",
        ai_feedback=feedback_result["feedback"],
        is_correct=feedback_result["is_correct"]
    )
    
    # Award skill badge if correct
    if feedback_result["is_correct"]:
        badge = badge_map.get(simulation_id)
        if badge and badge not in current_user.skill_badges:
            submission.skill_badge_earned = badge
            await db.users.update_one(
                {"id": current_user.id},
                {"$addToSet": {"skill_badges": badge, "completed_simulations": simulation_id}}
            )
    
    await db.submissions.insert_one(submission.dict())
    return submission

# Initialize tech fields and simulations
@api_router.post("/admin/init-tech-fields")
async def initialize_tech_fields():
    """Initialize tech fields"""
    tech_fields = [
        {
            "id": "software-engineering",
            "name": "Software Engineering",
            "description": "Build, maintain, and scale software applications and systems",
            "icon": "💻",
            "color": "blue"
        },
        {
            "id": "cybersecurity",
            "name": "Cybersecurity",
            "description": "Protect systems, networks, and data from digital threats",
            "icon": "🔒",
            "color": "red"
        },
        {
            "id": "data-science",
            "name": "Data Science",
            "description": "Extract insights and build predictive models from data",
            "icon": "📊",
            "color": "green"
        },
        {
            "id": "devops",
            "name": "DevOps",
            "description": "Bridge development and operations for faster, reliable deployments",
            "icon": "⚙️",
            "color": "purple"
        },
        {
            "id": "cloud-computing",
            "name": "Cloud Computing",
            "description": "Design and manage scalable cloud infrastructure and services",
            "icon": "☁️",
            "color": "sky"
        },
        {
            "id": "mobile-development",
            "name": "Mobile Development",
            "description": "Create native and cross-platform mobile applications",
            "icon": "📱",
            "color": "indigo"
        },
        {
            "id": "product-management",
            "name": "Product Management",
            "description": "Define product strategy, roadmap, and drive product development",
            "icon": "🎯",
            "color": "emerald"
        }
    ]
    
    for field in tech_fields:
        existing = await db.tech_fields.find_one({"id": field["id"]})
        if not existing:
            await db.tech_fields.insert_one(field)
    
    return {"message": f"Initialized {len(tech_fields)} tech fields successfully"}

@api_router.post("/admin/init-simulations")
async def initialize_simulations():
    """Initialize all tech simulations"""
    simulations = [
        # Software Engineering
        {
            "id": "se-debugging-1",
            "title": "Debug Shopping Cart Code",
            "description": "Find and fix critical bugs in a Python e-commerce shopping cart",
            "field_id": "software-engineering",
            "sub_field": "Debugging",
            "difficulty": "Medium",
            "estimated_time": "20 minutes",
            "briefing": "You're a software engineer on an e-commerce team. The shopping cart feature has been causing issues in production. Review the code and identify the bugs causing problems.",
            "instructions": "1. Download the Python code file\n2. Carefully review each function for logical errors\n3. Count the total number of bugs present\n4. Submit the number of bugs found",
            "task_type": "debugging",
            "expected_answer_type": "number",
            "questions": [
                {"id": "q1", "prompt": "How many critical bugs are hiding in this code that could crash the system under load?", "expected_answer_type": "number", "correct_answer": "5"},
                {"id": "q2", "prompt": "What's the most dangerous validation missing that hackers could exploit?", "expected_answer_type": "text", "correct_answer": "negative discount validation"}
            ]
        },
        {
            "id": "se-development-1",
            "title": "Build REST API Endpoint",
            "description": "Create a REST API endpoint for user authentication with proper validation",
            "field_id": "software-engineering",
            "sub_field": "Development",
            "difficulty": "Hard",
            "estimated_time": "30 minutes",
            "briefing": "You're a backend developer tasked with creating a user authentication endpoint. The frontend team needs a secure API that validates user credentials and returns appropriate responses.",
            "instructions": "1. Download the requirements document\n2. Implement the authentication endpoint\n3. Add proper input validation and error handling\n4. Submit the HTTP status code for successful login",
            "task_type": "development",
            "expected_answer_type": "number",
            "questions": [
                {"id": "q1", "prompt": "What HTTP status code indicates successful login?", "expected_answer_type": "number", "correct_answer": "200"},
                {"id": "q2", "prompt": "Should passwords be stored in plaintext? (yes/no)", "expected_answer_type": "text", "correct_answer": "no"},
                {"id": "q3", "prompt": "What security measure prevents brute force attacks?", "expected_answer_type": "text", "correct_answer": "rate limiting"}
            ]
        },
        {
            "id": "se-testing-1",
            "title": "Write Unit Tests",
            "description": "Create comprehensive unit tests for a calculator class",
            "field_id": "software-engineering",
            "sub_field": "Testing",
            "difficulty": "Easy",
            "estimated_time": "15 minutes",
            "briefing": "You're a QA engineer responsible for ensuring code quality. The development team has created a calculator class and needs you to write unit tests to verify all functionality works correctly.",
            "instructions": "1. Download the calculator class code\n2. Write unit tests for all methods\n3. Include edge cases and error conditions\n4. Submit the total number of test cases you would write",
            "task_type": "testing",
            "expected_answer_type": "number",
            "questions": [
                {"id": "q1", "prompt": "How many unit tests will you write?", "expected_answer_type": "number", "correct_answer": "7"},
                {"id": "q2", "prompt": "Name one edge case to test.", "expected_answer_type": "text", "correct_answer": "division by zero"}
            ]
        },
        
        # Cybersecurity
        {
            "id": "cyber-password-1",
            "title": "Password Security Assessment",
            "description": "Analyze password hashes to identify security vulnerabilities",
            "field_id": "cybersecurity",
            "sub_field": "Security Analysis",
            "difficulty": "Medium",
            "estimated_time": "20 minutes",
            "briefing": "You're a cybersecurity analyst conducting a security audit. A client's password database was compromised. Your job is to crack the hashes and assess the security risk.",
            "instructions": "1. Download the password hash file\n2. Use the provided wordlist to crack the MD5 hashes\n3. Identify at least 3 cracked passwords\n4. Submit the passwords separated by commas",
            "task_type": "security",
            "expected_answer_type": "list",
            "questions": [
                {"id": "q1", "prompt": "Provide at least two cracked passwords (comma-separated)", "expected_answer_type": "list", "correct_answer": "password123,admin,letmein"},
                {"id": "q2", "prompt": "What hash algorithm is used?", "expected_answer_type": "text", "correct_answer": "md5"}
            ]
        },
        {
            "id": "cyber-penetration-1",
            "title": "Network Vulnerability Scan",
            "description": "Identify security vulnerabilities in a network configuration",
            "field_id": "cybersecurity",
            "sub_field": "Penetration Testing",
            "difficulty": "Hard",
            "estimated_time": "25 minutes",
            "briefing": "You're a penetration tester conducting a security assessment. The client wants you to identify potential vulnerabilities in their network configuration and suggest remediation steps.",
            "instructions": "1. Download the network configuration file\n2. Analyze the setup for common vulnerabilities\n3. Identify the most critical security issue\n4. Submit the vulnerability type (e.g., 'open_port', 'weak_encryption', 'default_credentials')",
            "task_type": "security",
            "expected_answer_type": "text",
            "questions": [
                {"id": "q1", "prompt": "What is the most critical vulnerability?", "expected_answer_type": "text", "correct_answer": "default_credentials"},
                {"id": "q2", "prompt": "Is telnet enabled? (yes/no)", "expected_answer_type": "text", "correct_answer": "yes"},
                {"id": "q3", "prompt": "How many minutes would it take to exploit this network?", "expected_answer_type": "number", "correct_answer": "5"}
            ]
        },
        
        # Data Science
        {
            "id": "ds-analysis-1",
            "title": "Customer Churn Prediction",
            "description": "Analyze customer data to predict churn probability",
            "field_id": "data-science",
            "sub_field": "Data Analysis",
            "difficulty": "Medium",
            "estimated_time": "25 minutes",
            "briefing": "You're a data scientist at a SaaS company. The product team wants to understand which customers are likely to churn so they can implement retention strategies.",
            "instructions": "1. Download the customer dataset\n2. Analyze the correlation between features and churn\n3. Identify the strongest predictor of churn\n4. Submit the feature name with highest correlation",
            "task_type": "analysis",
            "expected_answer_type": "text",
            "questions": [
                {"id": "q1", "prompt": "Which feature has the strongest correlation with churn?", "expected_answer_type": "text", "correct_answer": "Monthly_Charges"},
                {"id": "q2", "prompt": "Is churn higher for month-to-month contracts? (yes/no)", "expected_answer_type": "text", "correct_answer": "yes"},
                {"id": "q3", "prompt": "Name one feature that reduces churn risk.", "expected_answer_type": "text", "correct_answer": "online_security"}
            ]
        },
        {
            "id": "ds-modeling-1",
            "title": "Build ML Pipeline",
            "description": "Create a machine learning pipeline for email classification",
            "field_id": "data-science",
            "sub_field": "Machine Learning",
            "difficulty": "Hard",
            "estimated_time": "35 minutes",
            "briefing": "You're a machine learning engineer tasked with building an email spam classifier. The marketing team needs to automatically filter spam emails from their customer communications.",
            "instructions": "1. Download the email dataset\n2. Preprocess the text data\n3. Choose appropriate features and model\n4. Submit the accuracy percentage of your model",
            "task_type": "development",
            "expected_answer_type": "percentage",
            "questions": [
                {"id": "q1", "prompt": "What's your AI guardian's kill rate against spam? (accuracy percentage, e.g., 85%)", "expected_answer_type": "percentage", "correct_answer": "85%"},
                {"id": "q2", "prompt": "Which classic algorithm is your spam-fighting champion?", "expected_answer_type": "text", "correct_answer": "naive bayes"},
                {"id": "q3", "prompt": "What's your secret weapon for turning text into model ammunition?", "expected_answer_type": "text", "correct_answer": "tf-idf"}
            ]
        },
        
        # DevOps
        {
            "id": "devops-deployment-1",
            "title": "Docker Containerization",
            "description": "Containerize a web application using Docker",
            "field_id": "devops",
            "sub_field": "Deployment",
            "difficulty": "Medium",
            "estimated_time": "20 minutes",
            "briefing": "You're tasked with containerizing a small web application so it runs consistently across environments. Use Docker to define the base image, install dependencies, copy application code, and configure the runtime. Focus on small image size, security, and repeatable builds.",
            "instructions": "1. Download the application code\n2. Create a Dockerfile with: base image, dependencies, application files, and runtime configuration\n3. Optimize for size and security (pin versions, use a small base image, limit layers)\n4. Build and run the image locally to verify\n5. Submit a summary of your image layers and choices",
            "task_type": "development",
            "expected_answer_type": "number",
            "questions": [
                {"id": "q1", "prompt": "How many strategic layers does your Docker fortress have?", "expected_answer_type": "number", "correct_answer": "4"},
                {"id": "q2", "prompt": "Should you pin dependency versions to avoid chaos? (yes/no)", "expected_answer_type": "text", "correct_answer": "yes"},
                {"id": "q3", "prompt": "What's your secret weapon for creating lightweight containers?", "expected_answer_type": "text", "correct_answer": "alpine"}
            ]
        },
        {
            "id": "devops-monitoring-1",
            "title": "Set Up Application Monitoring",
            "description": "Configure monitoring and alerting for a production application",
            "field_id": "devops",
            "sub_field": "Monitoring",
            "difficulty": "Hard",
            "estimated_time": "30 minutes",
            "briefing": "Design and configure a practical monitoring and alerting setup for a production web application. Ensure coverage across performance, errors, availability, and infrastructure resources. Provide clear alert thresholds and a dashboard plan for day-to-day visibility.",
            "instructions": "1. Download the application architecture blueprint\n2. Define monitoring coverage: latency, error rate, traffic, saturation, uptime, database and resource metrics\n3. Configure alert thresholds and notification routes for critical events\n4. Build dashboards that surface key service and infrastructure views\n5. Submit a concise summary of rules, thresholds, and dashboards",
            "task_type": "analysis",
            "expected_answer_type": "number",
            "questions": [
                {"id": "q1", "prompt": "How many critical monitoring rules will protect the empire?", "expected_answer_type": "number", "correct_answer": "6"},
                {"id": "q2", "prompt": "What's the most important metric for user happiness?", "expected_answer_type": "text", "correct_answer": "response time"},
                {"id": "q3", "prompt": "Which tool transforms metrics into visual masterpieces?", "expected_answer_type": "text", "correct_answer": "grafana"}
            ]
        },
        
        # Cloud Computing
        {
            "id": "cloud-aws-1",
            "title": "AWS Infrastructure Design",
            "description": "Design a scalable AWS infrastructure for a web application",
            "field_id": "cloud-computing",
            "sub_field": "Infrastructure",
            "difficulty": "Hard",
            "estimated_time": "30 minutes",
            "briefing": "You're a cloud architect designing infrastructure for a growing startup. The application needs to be highly available, scalable, and cost-effective on AWS.",
            "instructions": "1. Download the application requirements\n2. Design the AWS architecture\n3. Choose appropriate services and configurations\n4. Submit the number of AWS services you would use",
            "task_type": "analysis",
            "expected_answer_type": "number",
            "questions": [
                {"id": "q1", "prompt": "How many AWS services will you use?", "expected_answer_type": "number", "correct_answer": "12", "hints": ["Double digits."]},
                {"id": "q2", "prompt": "Name the DNS service in AWS.", "expected_answer_type": "text", "correct_answer": "route 53", "hints": ["Global DNS."]},
                {"id": "q3", "prompt": "Which service provides object storage?", "expected_answer_type": "text", "correct_answer": "s3", "hints": ["Buckets."]}
            ]
        },
        {
            "id": "cloud-security-1",
            "title": "Cloud Security Configuration",
            "description": "Configure security groups and IAM policies for cloud resources",
            "field_id": "cloud-computing",
            "sub_field": "Security",
            "difficulty": "Medium",
            "estimated_time": "25 minutes",
            "briefing": "You're a cloud security engineer responsible for securing AWS resources. The company has strict security requirements and needs proper access controls and network security.",
            "instructions": "1. Download the security requirements\n2. Configure IAM policies and security groups\n3. Implement least privilege access\n4. Submit the number of security groups you would create",
            "task_type": "security",
            "expected_answer_type": "number",
            "questions": [
                {"id": "q1", "prompt": "How many security groups will you create?", "expected_answer_type": "number", "correct_answer": "5", "hints": ["Each tier."]},
                {"id": "q2", "prompt": "Should all users have MFA? (yes/no)", "expected_answer_type": "text", "correct_answer": "yes", "hints": ["Best practice."]},
                {"id": "q3", "prompt": "Name the AWS key management service.", "expected_answer_type": "text", "correct_answer": "kms", "hints": ["Keys."]}
            ]
        },
        
        # Mobile Development
        {
            "id": "mobile-native-1",
            "title": "iOS App Performance Optimization",
            "description": "Optimize an iOS app for better performance and user experience",
            "field_id": "mobile-development",
            "sub_field": "Native Development",
            "difficulty": "Hard",
            "estimated_time": "30 minutes",
            "briefing": "You're an iOS developer working on a performance-critical app. Users are reporting slow load times and crashes. You need to identify and fix the performance bottlenecks.",
            "instructions": "1. Download the iOS app code\n2. Analyze performance issues\n3. Implement optimizations\n4. Submit the number of performance issues you identified",
            "task_type": "development",
            "expected_answer_type": "number",
            "questions": [
                {"id": "q1", "prompt": "How many performance issues can you spot?", "expected_answer_type": "number", "correct_answer": "8", "hints": ["Scroll, memory, threads."]},
                {"id": "q2", "prompt": "Name one threading-related issue.", "expected_answer_type": "text", "correct_answer": "main thread blocking", "hints": ["UI stalls."]},
                {"id": "q3", "prompt": "How should large images be loaded?", "expected_answer_type": "text", "correct_answer": "asynchronously", "hints": ["Not sync."]}
            ]
        },
        {
            "id": "mobile-cross-1",
            "title": "React Native State Management",
            "description": "Implement proper state management in a React Native app",
            "field_id": "mobile-development",
            "sub_field": "Cross-Platform",
            "difficulty": "Medium",
            "estimated_time": "25 minutes",
            "briefing": "You're a mobile developer working on a React Native app. The app's state management is becoming complex and causing bugs. You need to implement a proper state management solution.",
            "instructions": "1. Download the React Native app code\n2. Analyze the current state management\n3. Implement Redux or Context API\n4. Submit the number of reducers you would create",
            "task_type": "development",
            "expected_answer_type": "number",
            "questions": [
                {"id": "q1", "prompt": "How many reducers would you create?", "expected_answer_type": "number", "correct_answer": "3", "hints": ["User, UI, errors."]},
                {"id": "q2", "prompt": "Name one state management library.", "expected_answer_type": "text", "correct_answer": "redux", "hints": ["Popular choice."]},
                {"id": "q3", "prompt": "Is direct state mutation OK? (yes/no)", "expected_answer_type": "text", "correct_answer": "no", "hints": ["Immutable updates."]}
            ]
        },
        
        # Product Management
        {
            "id": "pm-strategy-1",
            "title": "Product Roadmap Planning",
            "description": "Create a product roadmap based on user research and business goals",
            "field_id": "product-management",
            "sub_field": "Strategy",
            "difficulty": "Hard",
            "estimated_time": "35 minutes",
            "briefing": "You're a Product Manager at a SaaS startup. The CEO wants you to create a 6-month product roadmap based on user feedback, market research, and business objectives. You need to prioritize features and create a timeline.",
            "instructions": "1. Download the user research data\n2. Analyze market trends and user needs\n3. Prioritize features using RICE scoring\n4. Submit the number of features you would include in Q1",
            "task_type": "analysis",
            "expected_answer_type": "number",
            "questions": [
                {"id": "q1", "prompt": "How many features in Q1?", "expected_answer_type": "number", "correct_answer": "5", "hints": ["RICE picks."]},
                {"id": "q2", "prompt": "Name one high-impact feature.", "expected_answer_type": "text", "correct_answer": "user authentication", "hints": ["Security basics."]},
                {"id": "q3", "prompt": "Which prioritization method was suggested?", "expected_answer_type": "text", "correct_answer": "rice", "hints": ["Acronym."]}
            ]
        },
        {
            "id": "pm-analytics-1",
            "title": "Product Metrics Analysis",
            "description": "Analyze product metrics to identify growth opportunities",
            "field_id": "product-management",
            "sub_field": "Analytics",
            "difficulty": "Medium",
            "estimated_time": "25 minutes",
            "briefing": "You're a Product Manager analyzing your app's performance. The team needs insights on user behavior, feature adoption, and conversion funnels to make data-driven product decisions.",
            "instructions": "1. Download the product analytics data\n2. Identify key trends and patterns\n3. Calculate the most important metric\n4. Submit the conversion rate percentage",
            "task_type": "analysis",
            "expected_answer_type": "percentage",
            "questions": [
                {"id": "q1", "prompt": "What is the conversion rate?", "expected_answer_type": "percentage", "correct_answer": "12.5%", "hints": ["Leads/users."]},
                {"id": "q2", "prompt": "Name one metric trending down.", "expected_answer_type": "text", "correct_answer": "bounce rate", "hints": ["Look at arrows."]},
                {"id": "q3", "prompt": "Which metric indicates engagement duration?", "expected_answer_type": "text", "correct_answer": "average session duration", "hints": ["Time spent."]}
            ]
        },
        {
            "id": "pm-user-research-1",
            "title": "User Interview Analysis",
            "description": "Analyze user interview data to identify key insights and pain points",
            "field_id": "product-management",
            "sub_field": "User Research",
            "difficulty": "Easy",
            "estimated_time": "20 minutes",
            "briefing": "You're a Product Manager who just completed 20 user interviews. You need to analyze the feedback to identify the most common pain points and prioritize product improvements.",
            "instructions": "1. Download the user interview transcripts\n2. Identify common themes and pain points\n3. Categorize feedback by priority\n4. Submit the most frequently mentioned pain point",
            "task_type": "research",
            "expected_answer_type": "text",
            "questions": [
                {"id": "q1", "prompt": "Most frequent pain point?", "expected_answer_type": "text", "correct_answer": "slow_loading", "hints": ["Repeated many times."]},
                {"id": "q2", "prompt": "How many participants?", "expected_answer_type": "number", "correct_answer": "20", "hints": ["Two digits."]},
                {"id": "q3", "prompt": "Name one improvement requested.", "expected_answer_type": "text", "correct_answer": "dark mode", "hints": ["Theme option."]}
            ]
        }
    ]
    
    for sim in simulations:
        # Use upsert to replace existing simulations with new content
        await db.simulations.replace_one(
            {"id": sim["id"]}, 
            sim, 
            upsert=True
        )
    
    return {"message": f"Initialized {len(simulations)} tech simulations successfully"}


@api_router.post("/admin/merge-simulation-questions")
async def merge_simulation_questions():
    """Merge questions/hints/checklist into existing simulations without recreating them."""
    updates = {
        # Software Engineering
        "se-debugging-1": {
            "questions": [
                {"id": "q1", "prompt": "How many logic bugs are present?", "expected_answer_type": "number", "correct_answer": "5", "hints": ["Scan for assignment vs comparison (==)", "Check edge cases in checkout flow"]},
                {"id": "q2", "prompt": "Name one validation missing in discount handling.", "expected_answer_type": "text", "correct_answer": "negative discount", "hints": ["Validate input range before applying", "Percent should not be below 0 or above 100"]}
            ],
           
        },
        "se-development-1": {
            "questions": [
                {"id": "q1", "prompt": "What HTTP status code indicates successful login?", "expected_answer_type": "number", "correct_answer": "200", "hints": ["2xx means success", "Common OK status"]},
                {"id": "q2", "prompt": "Should passwords be stored in plaintext? (yes/no)", "expected_answer_type": "text", "correct_answer": "no", "hints": ["Use hashing with salt", "Think about security best practices"]}
            ]
        },
        "se-testing-1": {
            "questions": [
                {"id": "q1", "prompt": "How many unit tests will you write?", "expected_answer_type": "number", "correct_answer": "7", "hints": ["Cover happy paths and errors", "Think about boundaries"]},
                {"id": "q2", "prompt": "Name one edge case to test.", "expected_answer_type": "text", "correct_answer": "division by zero", "hints": ["Invalid inputs", "Exceptional conditions"]}
            ]
        },
        # Cybersecurity
        "cyber-password-1": {
            "questions": [
                {"id": "q1", "prompt": "Provide at least two cracked passwords (comma-separated)", "expected_answer_type": "list", "correct_answer": "password123,admin,letmein", "hints": ["Start with common weak passwords", "Use the provided wordlist"]},
                {"id": "q2", "prompt": "What hash algorithm is used?", "expected_answer_type": "text", "correct_answer": "md5", "hints": ["Look at the file header/title", "It's a widely known legacy hash"]}
            ]
        },
        "cyber-penetration-1": {
            "questions": [
                {"id": "q1", "prompt": "What is the most critical vulnerability?", "expected_answer_type": "text", "correct_answer": "default_credentials", "hints": ["Think about easy entry points", "Factory settings often remain unchanged"]},
                {"id": "q2", "prompt": "Is telnet enabled? (yes/no)", "expected_answer_type": "text", "correct_answer": "yes", "hints": ["Check legacy services", "Insecure remote access"]},
                {"id": "q3", "prompt": "How many minutes would it take a real hacker to exploit this network?", "expected_answer_type": "number", "correct_answer": "5", "hints": ["Single-digit estimate", "Quick win for attackers"]}
            ]
        },
        # Data Science
        "ds-analysis-1": {
            "questions": [
                {"id": "q1", "prompt": "Which feature has the strongest correlation with churn?", "expected_answer_type": "text", "correct_answer": "Monthly_Charges", "hints": ["Look at continuous pricing data", "Higher bills often drive churn"]},
                {"id": "q2", "prompt": "Is churn higher for month-to-month contracts? (yes/no)", "expected_answer_type": "text", "correct_answer": "yes", "hints": ["Commitment length matters", "Short-term plans"]},
                {"id": "q3", "prompt": "Name one feature that reduces churn risk.", "expected_answer_type": "text", "correct_answer": "online_security", "hints": ["Value-added services help retention", "Think protection features"]}
            ]
        },
        "ds-modeling-1": {
            "questions": [
                {"id": "q1", "prompt": "What accuracy did your model achieve? (e.g., 85%)", "expected_answer_type": "percentage", "correct_answer": "85%", "hints": ["Two digits and a %", "Aim for mid-80s"]},
                {"id": "q2", "prompt": "Name one model suitable for spam detection.", "expected_answer_type": "text", "correct_answer": "naive bayes", "hints": ["Classic probabilistic model", "Also consider SVM"]},
                {"id": "q3", "prompt": "Name a common text feature extraction method.", "expected_answer_type": "text", "correct_answer": "tf-idf", "hints": ["Term weighting", "Beyond bag-of-words"]}
            ]
        },
        # DevOps
        "devops-deployment-1": {
            "questions": [
                {"id": "q1", "prompt": "How many layers are in your Docker image?", "expected_answer_type": "number", "correct_answer": "4", "hints": ["Base, deps, code, runtime", "Think build layering"]},
                {"id": "q2", "prompt": "Should you pin dependency versions? (yes/no)", "expected_answer_type": "text", "correct_answer": "yes", "hints": ["Repeatable builds", "Avoid 'latest'"]},
                {"id": "q3", "prompt": "Name one way to reduce image size.", "expected_answer_type": "text", "correct_answer": "alpine", "hints": ["Choose smaller base images", "Multi-stage builds help"]}
            ]
        },
        "devops-monitoring-1": {
            "questions": [
                {"id": "q1", "prompt": "How many monitoring rules will you create?", "expected_answer_type": "number", "correct_answer": "6", "hints": ["Cover latency, errors, traffic", "Don't forget resource saturation"]},
                {"id": "q2", "prompt": "Name one metric for performance SLOs.", "expected_answer_type": "text", "correct_answer": "response time", "hints": ["User-facing latency", "Think UX"]},
                {"id": "q3", "prompt": "Which tool visualizes metrics?", "expected_answer_type": "text", "correct_answer": "grafana", "hints": ["Often paired with Prometheus", "Dashboards"]}
            ]
        },
        # Cloud
        "cloud-aws-1": {
            "questions": [
                {"id": "q1", "prompt": "How many AWS services will you use?", "expected_answer_type": "number", "correct_answer": "12", "hints": ["Double digits."]},
                {"id": "q2", "prompt": "Name the DNS service in AWS.", "expected_answer_type": "text", "correct_answer": "route 53", "hints": ["Global DNS."]},
                {"id": "q3", "prompt": "Which service provides object storage?", "expected_answer_type": "text", "correct_answer": "s3", "hints": ["Buckets."]}
            ]
        },
        "cloud-security-1": {
            "questions": [
                {"id": "q1", "prompt": "How many security groups will you create?", "expected_answer_type": "number", "correct_answer": "5", "hints": ["Each tier."]},
                {"id": "q2", "prompt": "Should all users have MFA? (yes/no)", "expected_answer_type": "text", "correct_answer": "yes", "hints": ["Best practice."]},
                {"id": "q3", "prompt": "Name the AWS key management service.", "expected_answer_type": "text", "correct_answer": "kms", "hints": ["Keys."]}
            ]
        },
        # Mobile
        "mobile-native-1": {
            "questions": [
                {"id": "q1", "prompt": "How many performance issues can you spot?", "expected_answer_type": "number", "correct_answer": "8", "hints": ["Scroll, memory, threads."]},
                {"id": "q2", "prompt": "Name one threading-related issue.", "expected_answer_type": "text", "correct_answer": "main thread blocking", "hints": ["UI stalls."]},
                {"id": "q3", "prompt": "How should large images be loaded?", "expected_answer_type": "text", "correct_answer": "asynchronously", "hints": ["Not sync."]}
            ]
        },
        "mobile-cross-1": {
            "questions": [
                {"id": "q1", "prompt": "How many reducers would you create?", "expected_answer_type": "number", "correct_answer": "3", "hints": ["User, UI, errors."]},
                {"id": "q2", "prompt": "Name one state management library.", "expected_answer_type": "text", "correct_answer": "redux", "hints": ["Popular choice."]},
                {"id": "q3", "prompt": "Is direct state mutation OK? (yes/no)", "expected_answer_type": "text", "correct_answer": "no", "hints": ["Immutable updates."]}
            ]
        },
        # Product
        "pm-strategy-1": {
            "questions": [
                {"id": "q1", "prompt": "How many features in Q1?", "expected_answer_type": "number", "correct_answer": "5", "hints": ["RICE picks."]},
                {"id": "q2", "prompt": "Name one high-impact feature.", "expected_answer_type": "text", "correct_answer": "user authentication", "hints": ["Security basics."]},
                {"id": "q3", "prompt": "Which prioritization method was suggested?", "expected_answer_type": "text", "correct_answer": "rice", "hints": ["Acronym."]}
            ]
        },
        "pm-analytics-1": {
            "questions": [
                {"id": "q1", "prompt": "What is the conversion rate?", "expected_answer_type": "percentage", "correct_answer": "12.5%", "hints": ["Leads/users."]},
                {"id": "q2", "prompt": "Name one metric trending down.", "expected_answer_type": "text", "correct_answer": "bounce rate", "hints": ["Look at arrows."]},
                {"id": "q3", "prompt": "Which metric indicates engagement duration?", "expected_answer_type": "text", "correct_answer": "average session duration", "hints": ["Time spent."]}
            ]
        },
        "pm-user-research-1": {
            "questions": [
                {"id": "q1", "prompt": "Most frequent pain point?", "expected_answer_type": "text", "correct_answer": "slow_loading", "hints": ["Repeated many times."]},
                {"id": "q2", "prompt": "How many participants?", "expected_answer_type": "number", "correct_answer": "20", "hints": ["Two digits."]},
                {"id": "q3", "prompt": "Name one improvement requested.", "expected_answer_type": "text", "correct_answer": "dark mode", "hints": ["Theme option."]}
            ]
        },
    }

    updated = 0
    for sim_id, payload in updates.items():
        res = await db.simulations.update_one(
            {"id": sim_id},
            {"$set": {k: v for k, v in payload.items()}},
        )
        if res.matched_count:
            updated += 1

    return {"message": f"Merged questions into {updated} existing simulations"}

# Split out admin simulation routes
try:
    from .simulations_routes import router as simulations_admin_router
except ImportError:
    from simulations_routes import router as simulations_admin_router

# Include the router in the main app
app.include_router(api_router)
app.include_router(simulations_admin_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database cleanup is handled automatically by FastAPI lifespan
