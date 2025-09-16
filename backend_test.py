import requests
import sys
import json
import base64
from datetime import datetime
import time

class PathfinderAPITester:
    def __init__(self, base_url="https://tryjobs.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 500:
                        print(f"   Response: {response_data}")
                    elif isinstance(response_data, list):
                        print(f"   Response: List with {len(response_data)} items")
                    return success, response_data
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timeout (30s)")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_register(self, email, username, password):
        """Test user registration"""
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data={"email": email, "username": username, "password": password}
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            print(f"   Token received: {self.token[:20]}...")
            return True
        return False

    def test_login(self, email, password):
        """Test user login"""
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data={"email": email, "password": password}
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            print(f"   Token received: {self.token[:20]}...")
            return True
        return False

    def test_get_user_profile(self):
        """Test getting current user profile"""
        success, response = self.run_test(
            "Get User Profile",
            "GET",
            "auth/me",
            200
        )
        if success and 'id' in response:
            self.user_id = response['id']
            print(f"   User ID: {self.user_id}")
            print(f"   Username: {response.get('username')}")
            print(f"   Skill Badges: {len(response.get('skill_badges', []))}")
            return True
        return False

    def test_initialize_simulations(self):
        """Test initializing default simulations"""
        success, response = self.run_test(
            "Initialize Simulations",
            "POST",
            "admin/init-simulations",
            200
        )
        return success

    def test_get_simulations(self):
        """Test getting all simulations"""
        success, response = self.run_test(
            "Get All Simulations",
            "GET",
            "simulations",
            200
        )
        if success and isinstance(response, list):
            print(f"   Found {len(response)} simulations")
            for sim in response:
                print(f"   - {sim.get('title')} ({sim.get('id')})")
            return response
        return []

    def test_get_simulation_file(self, simulation_id, expected_filename):
        """Test downloading simulation file"""
        success, response = self.run_test(
            f"Download File for {simulation_id}",
            "GET",
            f"simulations/{simulation_id}/file",
            200
        )
        if success and 'filename' in response and 'content' in response:
            filename = response['filename']
            content = response['content']
            mime_type = response.get('mime_type', '')
            
            print(f"   Filename: {filename}")
            print(f"   MIME Type: {mime_type}")
            print(f"   Content Length: {len(content)} characters (base64)")
            
            # Verify it's valid base64
            try:
                decoded = base64.b64decode(content)
                print(f"   Decoded Size: {len(decoded)} bytes")
                return filename == expected_filename
            except Exception as e:
                print(f"   ❌ Invalid base64 content: {e}")
                return False
        return False

    def test_submit_answer(self, simulation_id, answer):
        """Test submitting an answer to a simulation"""
        print(f"   Submitting answer: '{answer}' for simulation: {simulation_id}")
        success, response = self.run_test(
            f"Submit Answer for {simulation_id}",
            "POST",
            "simulations/submit",
            200,
            data={"simulation_id": simulation_id, "answer": answer}
        )
        if success:
            print(f"   Answer: {response.get('answer')}")
            print(f"   AI Feedback: {response.get('ai_feedback', 'No feedback')[:100]}...")
            print(f"   Is Correct: {response.get('is_correct')}")
            if response.get('skill_badge_earned'):
                print(f"   🏆 Badge Earned: {response.get('skill_badge_earned')}")
            return True
        return False

def main():
    print("🚀 Starting Project Pathfinder API Testing - All 10 Simulations")
    print("=" * 70)
    
    # Setup
    tester = PathfinderAPITester()
    test_timestamp = datetime.now().strftime('%H%M%S')
    test_email = f"test_{test_timestamp}@pathfinder.com"
    test_username = f"testuser_{test_timestamp}"
    test_password = "TestPass123!"

    print(f"Test User: {test_email}")
    print(f"Username: {test_username}")
    print(f"Backend URL: {tester.base_url}")

    # Test 1: User Registration
    if not tester.test_register(test_email, test_username, test_password):
        print("❌ Registration failed, stopping tests")
        return 1

    # Test 2: Get User Profile
    if not tester.test_get_user_profile():
        print("❌ Failed to get user profile")
        return 1

    # Test 3: Initialize Simulations
    tester.test_initialize_simulations()

    # Test 4: Get All Simulations
    simulations = tester.test_get_simulations()
    if not simulations:
        print("❌ No simulations found")
        return 1

    # Test 5: Test File Downloads for All 10 Simulations
    expected_files = {
        'business-analysis-1': 'Q3_Sales_Analysis.xlsx',
        'digital-marketing-1': 'Website_Analytics_Report.csv',
        'cybersecurity-1': 'password_hashes.txt',
        'paralegal-1': 'Software_License_Agreement.pdf',
        'data-science-1': 'Customer_Satisfaction_Dataset.xlsx',
        'ux-design-1': 'UX_Research_Report.pdf',
        'content-marketing-1': 'Content_Performance_Analysis.xlsx',
        'financial-analysis-1': 'Investment_Portfolio_Analysis.xlsx',
        'hr-recruiting-1': 'Candidate_Evaluation_Report.pdf',
        'software-dev-1': 'shopping_cart_debug.py'
    }
    
    found_simulations = {}
    
    for sim in simulations:
        sim_id = sim.get('id')
        if sim_id in expected_files:
            found_simulations[sim_id] = sim
            print(f"\n📁 Testing file download for {sim.get('title')}...")
            tester.test_get_simulation_file(sim_id, expected_files[sim_id])

    # Check for missing simulations
    missing_sims = set(expected_files.keys()) - set(found_simulations.keys())
    if missing_sims:
        print(f"⚠️  Missing simulations: {', '.join(missing_sims)}")
    else:
        print("✅ All 10 expected simulations found!")

    # Test 6: Submit Answers with Expected Correct Answers
    print("\n🤖 Testing AI Feedback System with All Simulations...")
    print("Note: AI responses may take 5-10 seconds each...")
    
    # Expected correct answers from the review request
    correct_answers = {
        "business-analysis-1": "5600",
        "digital-marketing-1": "68%",
        "cybersecurity-1": "password123,admin,letmein",
        "paralegal-1": "TechFlow Solutions Inc",
        "data-science-1": "negative",
        "ux-design-1": "checkout",
        "content-marketing-1": "webinar",
        "financial-analysis-1": "HealthPlus Inc",
        "hr-recruiting-1": "B",
        "software-dev-1": "3"
    }
    
    # Test submissions for found simulations
    for sim_id in found_simulations:
        if sim_id in correct_answers:
            print(f"\n🎯 Testing {found_simulations[sim_id].get('title')}...")
            tester.test_submit_answer(sim_id, correct_answers[sim_id])
            time.sleep(3)  # Pause between AI requests

    # Test 7: Test Login with existing user
    print("\n🔐 Testing Login with existing credentials...")
    tester.token = None  # Clear token to test login
    if not tester.test_login(test_email, test_password):
        print("❌ Login with existing user failed")

    # Test 8: Test invalid login
    print("\n🔐 Testing Invalid Login...")
    tester.token = None
    success, _ = tester.run_test(
        "Invalid Login",
        "POST", 
        "auth/login",
        401,  # Expect 401 for invalid credentials
        data={"email": "invalid@test.com", "password": "wrongpass"}
    )

    # Print final results
    print("\n" + "=" * 70)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 70)
    print(f"Total Tests Run: {tester.tests_run}")
    print(f"Tests Passed: {tester.tests_passed}")
    print(f"Tests Failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("⚠️  Some tests failed - check logs above")
        return 1

if __name__ == "__main__":
    sys.exit(main())