"""
TFU_Class2b.py - Fyers API Authentication and Access Token Generator

This script demonstrates the OAuth authorization code flow for Fyers API,
guiding through login URL generation, user input of the auth code,
and access token retrieval.

Usage:
1. Populate your client_id (app_id) and secret_key (app_secret).
2. Run the script; it opens the login URL in your default browser.
3. After login, copy the auth code and paste it when prompted.
4. The script fetches and prints the access token.
5. Use the access token to initialize Fyers API model for further requests.

Note:
- redirect_uri must match your app's configured redirect URI.
- This script uses synchronous mode and basic console interaction.
"""

from fyers_api import accessToken
from fyers_api import fyersModel
import webbrowser
import sys


def validate_params(client_id: str, secret_key: str):
    """Validate that required parameters are not empty."""
    if not client_id.strip():
        print("Error: client_id (App ID) must not be empty. Please update the script with your App ID.")
        sys.exit(1)
    if not secret_key.strip():
        print("Error: secret_key (App Secret) must not be empty. Please update the script with your App Secret.")
        sys.exit(1)


def generate_authcode_url(client_id: str, secret_key: str, redirect_uri: str,
                          response_type: str, state: str, grant_type: str):
    """
    Create a SessionModel instance and generate the authentication code URL.
    Returns the URL string.
    """
    app_session = accessToken.SessionModel(
        client_id=client_id,
        redirect_uri=redirect_uri,
        response_type=response_type,
        state=state,
        secret_key=secret_key,
        grant_type=grant_type
    )
    url = app_session.generate_authcode()
    return app_session, url


def get_auth_code_from_user():
    """Prompt the user to enter the authorization code obtained from login redirect."""
    auth_code = input("\nEnter the Auth Code from the URL after login: ").strip()
    while not auth_code:
        print("Auth Code cannot be empty. Please enter a valid auth code.")
        auth_code = input("Enter the Auth Code: ").strip()
    return auth_code


def generate_access_token(app_session, auth_code: str):
    """
    Use the auth code to generate the access token.
    Returns the access token string on success, None on failure.
    """
    try:
        app_session.set_token(auth_code)
        response = app_session.generate_token()
        access_token = response.get("access_token", None)
        if access_token:
            print("\nSuccessfully generated access token.")
            print("Access Token:", access_token)
            return access_token
        else:
            print("\nFailed to generate access token. Response:")
            print(response)
            return None
    except Exception as e:
        print(f"\nException occurred while generating access token: {e}")
        return None


def main():
    # Configuration parameters - Replace with your actual app credentials
    REDIRECT_URI = "http://localhost:4003"  # Must match your app settings
    CLIENT_ID = ""     # Your App ID here
    SECRET_KEY = ""    # Your App Secret here

    RESPONSE_TYPE = "code"
    GRANT_TYPE = "authorization_code"
    STATE = "sample_state"

    print("=== Fyers API Authentication and Access Token Generator ===\n")

    validate_params(CLIENT_ID, SECRET_KEY)

    print("Generating authentication URL for login...")
    app_session, auth_url = generate_authcode_url(
        CLIENT_ID, SECRET_KEY, REDIRECT_URI, RESPONSE_TYPE, STATE, GRANT_TYPE
    )

    print(f"\nLogin URL:\n{auth_url}\n")
    try:
        print("Opening login URL in your default browser...")
        webbrowser.open(auth_url, new=1)
    except Exception as e:
        print(f"Failed to open browser automatically. Please open the URL manually. Error: {e}")

    print("\nPlease complete login and copy the auth code parameter from the redirected URL.")

    auth_code = get_auth_code_from_user()

    print("\nGenerating access token... Please wait.")
    access_token = generate_access_token(app_session, auth_code)

    if access_token:
        print("\nNow initializing the Fyers API model object with your access token...")
        # Initialize FyersModel - synchronous call example, adjust log_path as needed
        fyers = fyersModel.FyersModel(token=access_token, is_async=False, client_id=CLIENT_ID, log_path="/")
        print("Fyers model initialized. You can now proceed with API calls.\n")
    else:
        print("Access token generation failed. Please retry the authentication process.\n")


if __name__ == "__main__":
    main()

