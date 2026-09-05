import pyotp
import requests
import webbrowser
from urllib.parse import urlparse, parse_qs
from fyers_apiv3 import fyersModel
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FyersAuth:
    TOKEN_FILENAME = 'access_token.txt'

    def __init__(self):
        self.client_id = Config.CLIENT_ID
        self.secret_key = Config.SECRET_KEY
        self.redirect_uri = Config.REDIRECT_URI
        self.totp_key = Config.TOTP_KEY
        self.access_token = None
        self.fyers = None

    def create_session(self):
        """Create a Fyers session model."""
        return fyersModel.SessionModel(
            client_id=self.client_id,
            secret_key=self.secret_key,
            redirect_uri=self.redirect_uri,
            grant_type="authorization_code"
        )

    def generate_auth_url(self) -> str:
        """Generate authorization URL."""
        try:
            session = self.create_session()
            auth_url = session.generate_authcode()
            logger.info(f"Authorization URL: {auth_url}")
            return auth_url
        except Exception as e:
            logger.error(f"Error generating auth URL: {e}")
            return None

    def get_totp(self) -> str:
        """Generate TOTP code for 2FA."""
        try:
            totp = pyotp.TOTP(self.totp_key)
            return totp.now()
        except Exception as e:
            logger.error(f"Error generating TOTP: {e}")
            return None

    def authenticate(self, auth_code: str = None) -> bool:
        """Complete authentication process."""
        try:
            if not auth_code:
                # Step 1: Get authorization URL
                auth_url = self.generate_auth_url()
                if not auth_url:
                    return False

                print(f"Please visit: {auth_url}")
                print("After authorization, copy the 'auth_code' from the redirect URL")
                auth_code = input("Enter auth_code: ")

            # Step 2: Generate access token
            session = self.create_session()
            session.set_token(auth_code)
            response = session.generate_token()

            if response['code'] == 200:
                self.access_token = response['access_token']
                self.fyers = fyersModel.FyersModel(
                    client_id=self.client_id,
                    token=self.access_token
                )
                logger.info("Authentication successful!")
                return True
            else:
                logger.error(f"Authentication failed: {response}")
                return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    def get_profile(self):
        """Get user profile to verify authentication."""
        try:
            if not self.fyers:
                logger.error("Not authenticated")
                return None

            response = self.fyers.get_profile()
            if response['code'] == 200:
                logger.info(f"Profile: {response['data']}")
                return response['data']
            else:
                logger.error(f"Failed to get profile: {response}")
                return None
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return None

    def save_token(self) -> None:
        """Save access token to file."""
        try:
            if self.access_token:
                with open(self.TOKEN_FILENAME, 'w') as f:
                    f.write(self.access_token)
                logger.info(f"Token saved to {self.TOKEN_FILENAME}")
        except Exception as e:
            logger.error(f"Error saving token: {e}")

    def load_token(self) -> bool:
        """Load access token from file."""
        try:
            with open(self.TOKEN_FILENAME, 'r') as f:
                self.access_token = f.read().strip()

            # Initialize Fyers model
            self.fyers = fyersModel.FyersModel(
                client_id=self.client_id,
                token=self.access_token
            )

            # Verify token by getting profile
            profile = self.get_profile()
            if profile:
                logger.info("Token loaded successfully!")
                return True
            else:
                logger.error("Invalid token")
                return False
        except FileNotFoundError:
            logger.info("No saved token found")
            return False
        except Exception as e:
            logger.error(f"Error loading token: {e}")
            return False

if __name__ == "__main__":
    # Example usage
    auth = FyersAuth()

    # Try to load existing token
    if not auth.load_token():
        # If no valid token, authenticate
        if auth.authenticate():
            auth.save_token()

    # Test authentication
    profile = auth.get_profile()
    if profile:
        print("Authentication successful!")
        print(f":User  {profile.get('name', 'Unknown')}")
    else:
        print("Authentication failed!")
