# Vanish - A Social Platform

Vanish is a unique social platform where posts disappear after 3 hours. It's designed for authentic, in-the-moment sharing and entertainment rather than serving as a permanent repository of information.

## Features

- **Time Intensive Posts**: All posts automatically vanish after 3 hours
- **Real-time Countdown**: Visual indicators showing how much time remains for each post
- **User Authentication**: Complete registration and login system
- **User Profiles**: Personal profiles showing user information and their active posts
- **Responsive Design**: Works on desktop and mobile devices

## Technologies Used

- **Backend**: Python with Flask framework
- **Database**: SQLAlchemy (configured for SQLite by default, easily adaptable to other databases)
- **Frontend**: HTML, CSS, JavaScript
- **Task Scheduling**: APScheduler for automatic post deletion

## Installation
# To View Code, visit master branch

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/vanish.git
   cd vanish
   ```

2. Create a virtual environment and activate it:
   ```
   Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables (optional):
   ```
   export SECRET_KEY="your-secret-key"
   export DATABASE_URL="your-database-url"  # Default is SQLite
   ```

6. Run the application:
   ```
   python app.py
   ```

7. Open your browser and navigate to `http://localhost:5000`

## Project Structure

```
vanish/
├── app.py                 # Main Flask application
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── static/                # Static files (CSS, JS, images)
│   ├── css/
│   │   └── style.css      # Main stylesheet
│   ├── js/
│   │   └── script.js      # Frontend JavaScript
│   └── images/
├── templates/             # HTML templates
│   ├── base.html          # Base template with common elements
│   ├── index.html         # Homepage
│   ├── login.html         # Login page
│   ├── register.html      # Registration page
│   ├── feed.html          # Main feed of posts
│   └── profile.html       # User profile page
```

## How It Works

1. **Post Creation**: Users create posts that are stored in the database with a timestamp.
2. **Post Display**: When posts are displayed, the remaining time is calculated based on the creation timestamp.
3. **Frontend Timers**: JavaScript timers update the countdown in real-time, making posts vanish from the UI when time expires.
4. **Backend Cleanup**: A background scheduler runs every 10 minutes to delete expired posts from the database.

## Customization

- **Expiration Time**: Change the `POST_EXPIRATION_HOURS` in `config.py` to adjust how long posts last.
- **Styling**: Modify `static/css/style.css` to customize the appearance.
- **Database**: Update the `SQLALCHEMY_DATABASE_URI` in `config.py` to use a different database.

## Future Enhancements

- Add likes functionality
- Enhance privacy settings
- Add notification system

