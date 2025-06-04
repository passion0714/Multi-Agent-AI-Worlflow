# MERGE AI Multi-Agent Workflow System

A comprehensive multi-agent AI system for automating lead processing through voice calls and data entry. This system integrates with VAPI for voice calls, Lead Hoop for data entry, and AWS S3 for call recording storage.

## 🏗️ Architecture Overview

The system consists of two independent AI agents that communicate through a shared PostgreSQL database:

1. **Voice Agent**: Makes outbound calls via VAPI to confirm lead data and collect TCPA consent
2. **Data Entry Agent**: Automates data entry into Lead Hoop portal using UI automation

## 🚀 Features

- **Multi-Agent Architecture**: Independent agents with shared data store communication
- **Voice Call Automation**: Integration with VAPI and Zoe AI assistant
- **UI Automation**: Automated data entry into Lead Hoop portal
- **Call Recording Management**: Automatic upload to AWS S3 with Lead Hoop specifications
- **Real-time Dashboard**: Monitor workflow progress and agent status
- **CSV Import**: Bulk import leads from Go High Level exports
- **Comprehensive Logging**: Track all call attempts and data entry operations
- **Error Handling**: Retry logic and detailed error reporting
- **Scalable Design**: Built to handle up to 1000 entries per day

## 🛠️ Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **PostgreSQL**: Shared data store and state machine
- **SQLAlchemy**: ORM for database operations
- **Playwright**: UI automation for Lead Hoop
- **VAPI**: Voice AI integration
- **AWS S3**: Call recording storage
- **Celery**: Background task processing
- **Redis**: Task queue backend

### Frontend
- **React**: Modern UI framework
- **Material-UI**: Professional component library
- **React Query**: Data fetching and caching
- **Recharts**: Data visualization
- **React Router**: Navigation

## 📋 Prerequisites

- Python 3.12.4+
- Node.js 16+
- PostgreSQL 12+
- Redis (for background tasks)
- VAPI Account with Zoe assistant configured
- Lead Hoop account credentials
- AWS S3 access for call recordings

## 🔧 Installation & Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd merge-ai-workflow
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp env.example .env

# Configure environment variables (see Configuration section)
nano .env
```

### 3. Database Setup

```bash
# Create PostgreSQL database
createdb merge_ai_workflow

# Run database migrations
python -m alembic upgrade head
```

### 4. Frontend Setup

```bash
cd frontend
npm install
```

### 5. Install Playwright Browsers

```bash
playwright install chromium
```

## ⚙️ Configuration

Configure the following environment variables in your `.env` file:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/merge_ai_workflow

# VAPI Configuration
VAPI_API_KEY=your_vapi_api_key_here
VAPI_PHONE_NUMBER=your_vapi_phone_number
VAPI_ASSISTANT_ID=your_vapi_assistant_id

# Lead Hoop Configuration
LEADHOOP_LOGIN_URL=https://leadhoop.com/login
LEADHOOP_USERNAME=your_leadhoop_username
LEADHOOP_PASSWORD=your_leadhoop_password
LEADHOOP_PORTAL_URL=https://leadhoop.com/portal

# AWS S3 Configuration for Call Recordings
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_REGION=us-east-1
S3_BUCKET=leadhoop-recordings
S3_FOLDER=ieim/eluminus_merge_142
PUBLISHER_ID=142

# Redis Configuration (for Celery)
REDIS_URL=redis://localhost:6379/0

# Application Configuration
SECRET_KEY=your_secret_key_here
DEBUG=True
LOG_LEVEL=INFO
```

## 🚀 Running the Application

### Development Mode

1. **Start the Backend**:
```bash
# Terminal 1: Start FastAPI server
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start Redis (if not running as service)
redis-server

# Terminal 3: Start Celery worker (optional, for background tasks)
celery -A backend.main worker --loglevel=info
```

2. **Start the Frontend**:
```bash
# Terminal 4: Start React development server
cd frontend
npm start
```

3. **Access the Application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## 📊 Usage

### 1. Import Leads
- Navigate to the Leads page
- Click "Import CSV" to upload a CSV file from Go High Level
- Expected CSV columns: First Name, Last Name, Email, Phone, Address, City, State, Zip

### 2. Start Agents
- Use the play button in the header to start both agents
- Monitor agent status in real-time
- View progress on the Dashboard

### 3. Monitor Progress
- **Dashboard**: Overview of lead processing statistics
- **Leads**: Detailed view of all leads and their status
- **Call Logs**: History of all voice calls and recordings
- **Data Entry Logs**: History of all data entry attempts

### 4. Manual Operations
- Retry failed calls or data entries
- Manually mark leads as confirmed
- View call recordings and error screenshots

## 🔄 Workflow Process

1. **Lead Import**: Leads are imported from CSV with "pending" status
2. **Voice Agent**: Processes pending leads, makes VAPI calls
3. **Call Processing**: Zoe confirms data and collects TCPA consent
4. **Status Update**: Successful calls marked as "confirmed"
5. **Data Entry Agent**: Processes confirmed leads
6. **UI Automation**: Enters data into Lead Hoop portal
7. **Recording Upload**: Call recordings uploaded to S3
8. **Completion**: Successful entries marked as "entered"

## 📈 Scaling Considerations

### For High Volume (1000+ leads/day):

1. **Database Optimization**:
   - Add database indexes for frequently queried fields
   - Consider read replicas for reporting

2. **Agent Scaling**:
   - Run multiple instances of each agent
   - Implement proper locking mechanisms
   - Use Celery for distributed processing

3. **Infrastructure**:
   - Deploy on cloud platforms (AWS, GCP, Azure)
   - Use container orchestration (Docker, Kubernetes)
   - Implement monitoring and alerting

## 🐛 Troubleshooting

### Common Issues:

1. **Database Connection Errors**:
   - Verify PostgreSQL is running
   - Check DATABASE_URL configuration

2. **VAPI Call Failures**:
   - Verify VAPI API key and credentials
   - Check phone number format
   - Ensure Zoe assistant is properly configured

3. **Lead Hoop Login Issues**:
   - Verify credentials are correct
   - Check if Lead Hoop portal URL has changed
   - Review UI automation selectors

4. **S3 Upload Failures**:
   - Verify AWS credentials
   - Check bucket permissions
   - Ensure bucket exists and is accessible

### Debugging:

1. **Enable Debug Logging**:
   ```env
   DEBUG=True
   LOG_LEVEL=DEBUG
   ```

2. **View Agent Logs**:
   - Check console output for detailed error messages
   - Review database logs for failed operations

3. **UI Automation Debugging**:
   - Set Playwright to non-headless mode
   - Review screenshots saved on errors

## 🔒 Security Considerations

- Store sensitive credentials in environment variables
- Use HTTPS in production
- Implement proper authentication for the web interface
- Regularly rotate API keys and passwords
- Monitor for suspicious activity

## 📝 API Documentation

The FastAPI backend provides interactive API documentation at `/docs` when running in development mode. Key endpoints include:

- `POST /leads/import-csv/`: Import leads from CSV
- `GET /leads/`: List all leads
- `POST /agents/start`: Start both agents
- `POST /agents/stop`: Stop both agents
- `GET /stats/dashboard`: Get dashboard statistics
- `POST /webhooks/vapi`: VAPI webhook endpoint

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is proprietary software developed for MERGE AI.

## 📞 Support

For technical support or questions, please contact the development team.

---

**Note**: This system is designed for the specific workflow requirements of MERGE AI and integrates with their existing VAPI setup and Lead Hoop portal. Customization may be required for different use cases. 