"# 🤖 EchoBot - AI Chat Assistant

A modern, intelligent chatbot application with file upload support, user authentication, and beautiful UI.

## ✨ Features

- **🧠 AI-Powered Conversations** - Powered by Google Gemini API
- **📄 File Analysis** - Upload PDFs and images for AI analysis
- **👤 User Accounts** - Secure authentication with personal avatars
- **💾 Chat History** - Persistent conversation storage
- **🌙 Dark Mode** - Beautiful light/dark theme support
- **📱 Responsive Design** - Works on all devices
- **🔒 User Isolation** - Complete data privacy between users

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Google Gemini API key

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd Chatbot-test-1
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp env.example .env
   ```
   Edit `.env` and add your configuration:
   ```
   SECRET_KEY=your-super-secret-key-here
   GEMINI_API_KEY=your-gemini-api-key-here
   DATABASE_URL=sqlite:///chatbot.db
   DEBUG=False
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open in browser**
   Visit `http://localhost:5000`

## 🌐 Deployment

### Heroku Deployment

1. **Create a Heroku app**
   ```bash
   heroku create your-app-name
   ```

2. **Set environment variables**
   ```bash
   heroku config:set SECRET_KEY=your-secret-key
   heroku config:set GEMINI_API_KEY=your-gemini-api-key
   heroku config:set DATABASE_URL=your-database-url
   ```

3. **Deploy**
   ```bash
   git push heroku main
   ```

### Other Platforms
- **Railway**: Just connect your GitHub repo
- **Render**: Connect repo and set environment variables
- **DigitalOcean App Platform**: Deploy directly from GitHub

## 🔧 Configuration

### Environment Variables
- `SECRET_KEY`: Flask secret key for sessions
- `GEMINI_API_KEY`: Google Gemini API key
- `DATABASE_URL`: Database connection string
- `DEBUG`: Set to False in production
- `TESSERACT_CMD`: Path to Tesseract OCR binary

### File Uploads
- Supported formats: PDF, PNG, JPG, JPEG, GIF, WebP
- Maximum file size: 512MB
- OCR support for text extraction from images

## 🏗️ Project Structure

```
Chatbot-test-1/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── Procfile              # Heroku deployment config
├── runtime.txt           # Python version
├── static/               # Static assets
│   ├── script.js         # Frontend JavaScript
│   ├── avatars/          # User avatar uploads
│   └── public/           # CSS files
├── templates/            # HTML templates
│   ├── index.html        # Landing page
│   ├── chat.html         # Chat interface
│   ├── login.html        # Login page
│   ├── signup.html       # Registration page
│   └── profile.html      # User profile
├── user_uploads/         # User file uploads
└── instance/             # Database files
```

## 🛡️ Security Features

- ✅ Password hashing with Werkzeug
- ✅ User session management
- ✅ File upload validation
- ✅ User data isolation
- ✅ Secure API key handling
- ✅ CSRF protection ready

## 🎨 UI Features

- **Modern Design**: Clean, professional interface
- **Responsive Layout**: Works on desktop, tablet, and mobile
- **Avatar System**: Custom user avatars in chat and navigation
- **Theme Support**: Light and dark mode
- **Smooth Animations**: Enhanced user experience
- **File Preview**: Visual feedback for uploaded files

## 🔗 API Endpoints

- `POST /api/auth/signup` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/profile` - Get user profile
- `POST /api/profile/avatar` - Upload user avatar
- `POST /api/ai/chat` - Send message to AI
- `GET /api/chats` - Get chat history
- `POST /api/files` - Upload files

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the project
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📞 Support

For questions or issues, please open an issue on GitHub." 
