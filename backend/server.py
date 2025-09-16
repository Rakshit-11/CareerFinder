from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
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
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app without a prefix
app = FastAPI(title="Project Pathfinder API")

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

class Simulation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    category: str
    difficulty: str
    estimated_time: str
    briefing: str
    instructions: str
    task_type: str  # "calculation", "analysis", "find_value", "security", "research"
    expected_answer_type: str  # "number", "text", "percentage", "list", "code"

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
    answer: str

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
            
            # Different matching strategies for different answer types
            if simulation_id in ['cybersecurity-1']:  # Multiple passwords
                expected_passwords = correct_answer.split(',')
                user_passwords = [p.strip().lower() for p in user_answer.split(',')]
                is_correct = len(set(user_passwords) & set([p.strip().lower() for p in expected_passwords])) >= 2
            elif '%' in correct_answer or simulation_id in ['digital-marketing-1']:  # Percentage answers
                is_correct = user_clean == correct_clean or user_clean.replace('%', '') == correct_clean.replace('%', '')
            elif simulation_id in ['paralegal-1', 'ux-design-1']:  # Text/name answers
                is_correct = user_clean in correct_clean or correct_clean in user_clean
            else:  # Numeric answers
                try:
                    is_correct = float(user_clean.replace(',', '').replace('$', '')) == float(correct_clean.replace(',', '').replace('$', ''))
                except:
                    is_correct = user_clean == correct_clean
        else:
            is_correct = False
        
        # Generate contextual feedback based on simulation type and correctness
        feedback_templates = {
            'business-analysis-1': {
                'correct': "Excellent work! You've demonstrated strong analytical skills by correctly calculating the net profit. This type of financial analysis is crucial in business roles where you'll need to evaluate profitability and make data-driven decisions.",
                'incorrect': "Good effort on the business analysis task! Review the profit calculation formula: Net Profit = Revenue - (Cost of Goods + Operating Expenses + Marketing Spend + Other Expenses). Try recalculating with this approach."
            },
            'digital-marketing-1': {
                'correct': "Perfect! You've successfully identified the mobile bounce rate, showing strong attention to detail in analytics. Understanding user engagement metrics like this is essential for digital marketing success.",
                'incorrect': "Nice try on the marketing analytics task! Look for the 'Mobile Bounce Rate' row in the data. This metric helps marketers understand how mobile users interact with websites."
            },
            'cybersecurity-1': {
                'correct': "Outstanding! You've demonstrated cybersecurity awareness by identifying weak passwords. This skill is vital for security professionals who need to assess and improve password policies.",
                'incorrect': "Good attempt at the cybersecurity challenge! Try using the provided wordlist to crack the MD5 hashes. Common weak passwords like 'password123', 'admin', and 'letmein' are often found in security audits."
            },
            'paralegal-1': {
                'correct': "Excellent work! You've shown strong attention to detail in contract review, identifying the licensor correctly. This skill is essential for paralegals who need to extract key information from legal documents.",
                'incorrect': "Good effort on the contract review! Look for the 'Licensor' section in the agreement - it's the company granting the license. This type of careful reading is crucial in legal work."
            },
            'data-science-1': {
                'correct': "Great analysis! You've correctly identified the correlation pattern, showing strong data science intuition. Understanding relationships between variables is fundamental to data analysis and business intelligence.",
                'incorrect': "Good attempt at the data analysis! Consider how support calls might relate to customer satisfaction - more calls often indicate problems. Try analyzing the correlation between these two variables."
            },
            'ux-design-1': {
                'correct': "Perfect! You've identified the key UX issue correctly, demonstrating strong user research skills. This type of problem identification is crucial for UX designers who need to prioritize improvements.",
                'incorrect': "Good effort on the UX analysis! Review the research findings carefully - look for the most frequently mentioned problem area that affects the most users."
            },
            'content-marketing-1': {
                'correct': "Excellent work! You've identified the highest ROI content type, showing strong strategic thinking. This type of analysis helps content marketers allocate resources effectively.",
                'incorrect': "Nice try on the content analysis! Consider both engagement rates and conversion rates when evaluating ROI. Look for content types that generate leads efficiently relative to their cost."
            },
            'financial-analysis-1': {
                'correct': "Outstanding! You've made a solid investment recommendation based on financial metrics. This type of analysis is crucial for financial professionals who need to evaluate investment opportunities.",
                'incorrect': "Good attempt at the financial analysis! Consider factors like revenue growth, ROE, and debt levels when evaluating investments. Look for companies with strong growth potential and healthy financial ratios."
            },
            'hr-recruiting-1': {
                'correct': "Excellent decision! You've balanced technical skills, cultural fit, and cost considerations effectively. This type of evaluation is essential for HR professionals who need to make strategic hiring decisions.",
                'incorrect': "Good effort on the candidate evaluation! Consider the weighted criteria: technical competency (40%), cultural alignment (25%), experience relevance (20%), and cost consideration (15%)."
            },
            'software-dev-1': {
                'correct': "Perfect! You've identified all the bugs correctly, showing strong debugging skills. This type of code review is essential for software developers who need to maintain code quality.",
                'incorrect': "Good attempt at the debugging challenge! Look for common issues like assignment vs comparison operators, missing validation checks, and logical errors in the code."
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

# Simulation Routes
@api_router.get("/simulations", response_model=List[Simulation])
async def get_simulations():
    simulations = await db.simulations.find().to_list(1000)
    return [Simulation(**sim) for sim in simulations]

@api_router.get("/simulations/{simulation_id}", response_model=Simulation)
async def get_simulation(simulation_id: str):
    simulation = await db.simulations.find_one({"id": simulation_id})
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return Simulation(**simulation)

@api_router.get("/simulations/{simulation_id}/file", response_model=FileDownload)
async def get_simulation_file(simulation_id: str):
    """Generate and return the file for a specific simulation"""
    simulation = await db.simulations.find_one({"id": simulation_id})
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    file_generators = {
        "business-analysis-1": generate_business_analysis_file,
        "digital-marketing-1": generate_marketing_analytics_file,
        "cybersecurity-1": generate_cybersecurity_file,
        "paralegal-1": generate_paralegal_file,
        "data-science-1": generate_data_science_file,
        "ux-design-1": generate_ux_design_file,
        "content-marketing-1": generate_content_marketing_file,
        "financial-analysis-1": generate_financial_analysis_file,
        "hr-recruiting-1": generate_hr_recruiting_file,
        "software-dev-1": generate_software_dev_file
    }
    
    generator = file_generators.get(simulation_id)
    if not generator:
        raise HTTPException(status_code=404, detail="File not available for this simulation")
    
    return FileDownload(**generator())

@api_router.post("/simulations/submit", response_model=SimulationSubmission)
async def submit_simulation(
    submission_data: SubmissionCreate,
    current_user: User = Depends(get_current_user)
):
    # Correct answers mapping
    correct_answers = {
        "business-analysis-1": "5600",
        "digital-marketing-1": "68%",
        "cybersecurity-1": "password123,admin,letmein",  # Multiple correct passwords
        "paralegal-1": "TechFlow Solutions Inc",
        "data-science-1": "negative",  # Correlation is negative between support calls and satisfaction
        "ux-design-1": "checkout",  # Main pain point is checkout process
        "content-marketing-1": "webinar",  # Highest ROI content type
        "financial-analysis-1": "HealthPlus Inc",  # Best growth + ROE combination
        "hr-recruiting-1": "B",  # Marcus Chen - best value candidate
        "software-dev-1": "3"  # Number of bugs found
    }
    
    # Skill badge mapping
    badge_map = {
        "business-analysis-1": "Business Analysis Specialist",
        "digital-marketing-1": "Digital Marketing Analyst", 
        "cybersecurity-1": "Cybersecurity Apprentice",
        "paralegal-1": "Legal Document Reviewer",
        "data-science-1": "Data Analysis Professional",
        "ux-design-1": "UX Research Specialist", 
        "content-marketing-1": "Content Strategy Expert",
        "financial-analysis-1": "Investment Analysis Professional",
        "hr-recruiting-1": "Talent Acquisition Specialist",
        "software-dev-1": "Code Quality Inspector"
    }
    
    # Generate AI feedback
    correct_answer = correct_answers.get(submission_data.simulation_id)
    feedback_result = await generate_ai_feedback(
        submission_data.simulation_id,
        submission_data.answer,
        correct_answer
    )
    
    # Create submission
    submission = SimulationSubmission(
        user_id=current_user.id,
        simulation_id=submission_data.simulation_id,
        answer=submission_data.answer,
        ai_feedback=feedback_result["feedback"],
        is_correct=feedback_result["is_correct"]
    )
    
    # Award skill badge if correct
    if feedback_result["is_correct"]:
        badge = badge_map.get(submission_data.simulation_id)
        if badge and badge not in current_user.skill_badges:
            submission.skill_badge_earned = badge
            await db.users.update_one(
                {"id": current_user.id},
                {"$addToSet": {"skill_badges": badge, "completed_simulations": submission_data.simulation_id}}
            )
    
    await db.submissions.insert_one(submission.dict())
    return submission

# Initialize comprehensive simulations
@api_router.post("/admin/init-simulations")
async def initialize_simulations():
    """Initialize all career simulations"""
    simulations = [
        # Business & Finance
        {
            "id": "business-analysis-1",
            "title": "Calculate Net Profit",
            "description": "Analyze a Q3 sales spreadsheet and calculate the total net profit across all products and services.",
            "category": "Business Analysis",
            "difficulty": "Easy",
            "estimated_time": "15 minutes",
            "briefing": "You're a junior business analyst at a growing company. Your manager needs the Q3 net profit calculation for the board meeting tomorrow. You have the sales data with revenue and all associated costs.",
            "instructions": "1. Download the Excel file\n2. Calculate Net Profit = Revenue - (Cost of Goods + Operating Expenses + Marketing Spend + Other Expenses)\n3. Sum the net profit for all products/services\n4. Submit the total number",
            "task_type": "calculation",
            "expected_answer_type": "number"
        },
        {
            "id": "financial-analysis-1",
            "title": "Investment Portfolio Analysis", 
            "description": "Evaluate 5 investment opportunities and recommend the best stock based on growth potential and financial health.",
            "category": "Financial Analysis",
            "difficulty": "Medium",
            "estimated_time": "25 minutes",
            "briefing": "You're a junior investment analyst at a wealth management firm. A client wants to invest $50K in a growth stock. Analyze the financial metrics and identify the most promising investment.",
            "instructions": "1. Download the investment analysis spreadsheet\n2. Review metrics: PE ratio, revenue growth, ROE, debt levels\n3. Consider risk vs. return potential\n4. Submit the company name of your recommendation",
            "task_type": "analysis",
            "expected_answer_type": "text"
        },
        
        # Technology & Engineering  
        {
            "id": "cybersecurity-1",
            "title": "Password Security Assessment",
            "description": "Analyze password hashes to identify security vulnerabilities and assess password strength.",
            "category": "Cybersecurity",
            "difficulty": "Medium", 
            "estimated_time": "20 minutes",
            "briefing": "You're a cybersecurity analyst conducting a security audit. A client's password database was compromised. Your job is to crack the hashes and assess the security risk.",
            "instructions": "1. Download the password hash file\n2. Use the provided wordlist to crack the MD5 hashes\n3. Identify at least 3 cracked passwords\n4. Submit the passwords separated by commas",
            "task_type": "security",
            "expected_answer_type": "list"
        },
        {
            "id": "software-dev-1",
            "title": "Debug Shopping Cart Code",
            "description": "Review Python code for an e-commerce shopping cart and identify critical bugs that need fixing.",
            "category": "Software Development", 
            "difficulty": "Medium",
            "estimated_time": "20 minutes",
            "briefing": "You're a software developer on an e-commerce team. The shopping cart feature has been causing issues in production. Review the code and identify the bugs causing problems.",
            "instructions": "1. Download the Python code file\n2. Carefully review each function for logical errors\n3. Count the total number of bugs present\n4. Submit the number of bugs found",
            "task_type": "analysis",
            "expected_answer_type": "number"
        },
        
        # Marketing & Content
        {
            "id": "digital-marketing-1", 
            "title": "Find Mobile Bounce Rate",
            "description": "Analyze website analytics data to identify the mobile bounce rate and understand user engagement patterns.",
            "category": "Digital Marketing",
            "difficulty": "Easy",
            "estimated_time": "10 minutes", 
            "briefing": "You're a digital marketing analyst reviewing website performance. The marketing team is concerned about mobile user engagement and wants to know the current mobile bounce rate.",
            "instructions": "1. Download the analytics CSV file\n2. Look for the Mobile Bounce Rate in the data\n3. Submit the percentage value (include the % symbol)",
            "task_type": "find_value",
            "expected_answer_type": "percentage"
        },
        {
            "id": "content-marketing-1",
            "title": "Content ROI Analysis",
            "description": "Evaluate different content types and identify which delivers the best return on investment for lead generation.",
            "category": "Content Marketing",
            "difficulty": "Medium", 
            "estimated_time": "20 minutes",
            "briefing": "You're a content marketing specialist analyzing Q4 performance. The marketing director wants to know which content type generates the best ROI for the upcoming budget planning.",
            "instructions": "1. Download the content performance spreadsheet\n2. Calculate ROI by comparing lead generation to production costs\n3. Factor in engagement rates and conversion potential\n4. Submit the content type with highest overall value",
            "task_type": "analysis", 
            "expected_answer_type": "text"
        },
        
        # Design & Research
        {
            "id": "ux-design-1",
            "title": "UX Research Analysis", 
            "description": "Review user research findings and identify the primary pain point affecting user experience on a mobile app.",
            "category": "UX Design",
            "difficulty": "Easy",
            "estimated_time": "15 minutes",
            "briefing": "You're a UX researcher who just completed usability testing for a mobile e-commerce app. The product manager needs to know the top priority issue to fix in the next sprint.",
            "instructions": "1. Download the user research report\n2. Review user feedback and metrics\n3. Identify the most critical UX problem mentioned\n4. Submit the main issue (one word: navigation, checkout, search, etc.)",
            "task_type": "research",
            "expected_answer_type": "text"
        },
        
        # Data & Analytics
        {
            "id": "data-science-1",
            "title": "Customer Satisfaction Correlation",
            "description": "Analyze customer data to identify the relationship between support calls and satisfaction scores.",
            "category": "Data Science",
            "difficulty": "Medium",
            "estimated_time": "25 minutes", 
            "briefing": "You're a data scientist investigating customer satisfaction drivers. The customer success team wants to understand if support call frequency impacts satisfaction ratings.",
            "instructions": "1. Download the customer dataset\n2. Analyze the correlation between Support_Calls and Satisfaction_Score\n3. Determine if the relationship is positive or negative\n4. Submit your finding: 'positive' or 'negative'",
            "task_type": "analysis",
            "expected_answer_type": "text"
        },
        
        # Legal & HR
        {
            "id": "paralegal-1",
            "title": "Contract Review",
            "description": "Review a software license agreement and extract key information about the licensing company.",
            "category": "Legal/Paralegal", 
            "difficulty": "Easy",
            "estimated_time": "10 minutes",
            "briefing": "You're a paralegal assistant reviewing contracts for a client's legal matter. Your supervising attorney needs you to identify the licensing company from a software agreement.",
            "instructions": "1. Download the contract PDF\n2. Read through the agreement carefully\n3. Identify the company providing the license (the 'Licensor')\n4. Submit the exact company name as written in the contract",
            "task_type": "research", 
            "expected_answer_type": "text"
        },
        {
            "id": "hr-recruiting-1",
            "title": "Candidate Selection",
            "description": "Evaluate three software engineer candidates and recommend the best hire based on multiple criteria.",
            "category": "Human Resources",
            "difficulty": "Medium",
            "estimated_time": "20 minutes",
            "briefing": "You're an HR specialist working with the engineering team to fill a senior developer role. Review the candidate profiles and make a hiring recommendation that balances skills, culture fit, and budget.",
            "instructions": "1. Download the candidate evaluation report\n2. Consider technical skills, experience, cultural fit, and cost\n3. Apply the weighted criteria provided (40% technical, 25% culture, 20% experience, 15% cost)\n4. Submit the letter of your recommended candidate (A, B, or C)",
            "task_type": "analysis",
            "expected_answer_type": "text"
        }
    ]
    
    for sim in simulations:
        existing = await db.simulations.find_one({"id": sim["id"]})
        if not existing:
            await db.simulations.insert_one(sim)
    
    return {"message": f"Initialized {len(simulations)} career simulations successfully"}

# Include the router in the main app
app.include_router(api_router)

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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()