# YouTube Transcription Tool

A powerful tool for transcribing YouTube videos with automatic caption extraction and AI-powered speech recognition.

## Features

- **Video Transcription**: Convert YouTube videos to text using captions or OpenAI Whisper
- **Multiple Output Formats**: Download transcriptions as TXT, SRT, or VTT files
- **Batch Processing**: Transcribe multiple videos at once
- **Playlist Support**: Process entire YouTube playlists with a single request
- **OAuth Authentication**: Sign in with Google, Twitter, or Discord
- **User Dashboard**: Track transcription history and manage settings
- **Admin Panel**: Monitor usage and manage system settings

## Authentication Setup

The application supports OAuth authentication with Google, Twitter, and Discord. Follow these steps to set up authentication:

### Option 1: Quick Setup Using Admin Panel

1. Create an admin user by running:
   ```
   python create_admin.py your-email@example.com
   ```
   
2. Log in with any OAuth provider that matches your admin email
   
3. Navigate to Admin > OAuth Settings to configure providers

### Option 2: Manual Configuration

1. Register your application with OAuth providers:

   - **Google**: [Google Cloud Console](https://console.cloud.google.com/)
   - **Twitter**: [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
   - **Discord**: [Discord Developer Portal](https://discord.com/developers/applications)

2. Set the following callback URLs for each provider:
   - Google: `https://your-domain.com/auth/google/authorized`
   - Twitter: `https://your-domain.com/auth/twitter/authorized`
   - Discord: `https://your-domain.com/auth/discord/authorized`

3. Add the client IDs and secrets to your environment variables:
   ```
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   TWITTER_CLIENT_ID=your_twitter_client_id
   TWITTER_CLIENT_SECRET=your_twitter_client_secret
   DISCORD_CLIENT_ID=your_discord_client_id
   DISCORD_CLIENT_SECRET=your_discord_client_secret
   ```

## User Management

### User Roles

- **Regular Users**: Can transcribe videos and access their own history
- **Administrators**: Can access the admin panel, manage OAuth settings, and view system analytics

### Making a User an Administrator

1. Create an admin through the setup script:
   ```
   python create_admin.py target-email@example.com
   ```

2. Or update a user's admin status in the database directly:
   ```sql
   UPDATE users SET is_admin = TRUE WHERE email = 'target-email@example.com';
   ```

## Using the Transcription Tool

1. **Single Video Transcription**:
   - Enter a YouTube URL
   - Select transcription method (Auto, Captions, or Whisper)
   - Choose language (for Whisper)
   - Click "Transcribe Video"

2. **Batch Processing**:
   - Enter multiple YouTube URLs (one per line)
   - Configure settings
   - Click "Start Batch Processing"

3. **Playlist Processing**:
   - Enter a YouTube playlist URL
   - Configure settings
   - Click "Process Playlist"

## Technical Details

- Built with Flask and SQLAlchemy
- Uses OpenAI's Whisper for speech recognition
- Stores data in PostgreSQL database
- Supports OAuth 2.0 authentication
- Real-time progress updates

## Environment Variables

- `DATABASE_URL`: PostgreSQL database connection string
- `SESSION_SECRET`: Secret key for session encryption
- `OPENAI_API_KEY`: API key for OpenAI's Whisper service
- OAuth provider credentials (see Authentication Setup)

## Troubleshooting

If you encounter issues with OAuth login:

1. Check that the provider is enabled in Admin > OAuth Settings
2. Verify the correct client ID and secret are configured
3. Ensure the callback URL in your OAuth provider dashboard matches exactly
4. Check that your email address is the same across providers if using multiple

## License

This project is open source and available under the MIT license.