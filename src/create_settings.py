from requests_oauthlib import OAuth1Session
import sys
consumer_key = "WyfW9cnR6MFIri7VEbeF0eM2UlsfyusHVCJNI0XK"  # Identifier to associate our app with the user’s account
consumer_secret = "9a9NyeEaKPawZD7fVZmbc9HftGQiHttXzfItjvDW"  # To prove the authenticity of application during the OAuth process

# OAuth endpoints
request_token_url = "https://secure.splitwise.com/oauth/request_token"  # To get a request token (temporary token)
access_token_url = "https://secure.splitwise.com/oauth/access_token"  # To exchange the request token for an access token.
authorize_url = "https://secure.splitwise.com/oauth/authorize"  # To redirect the user to authorize the app

try:
    # Step 1: Obtain a request token
    oauth = OAuth1Session(consumer_key, client_secret=consumer_secret)  # Create an OAuth1Session object using your app's consumer key and secret
    fetch_response = oauth.fetch_request_token(request_token_url)  # Get a temporary request token and secret
    oauth_token = fetch_response.get("oauth_token") # Save the response in variable
    oauth_token_secret = fetch_response.get("oauth_token_secret")

    print("Request Token obtained:")
    print(f"oauth_token: {oauth_token}")
    print(f"oauth_token_secret: {oauth_token_secret}\n")

    # Step 2: Display the authorization URL for manual access
    auth_url = oauth.authorization_url(authorize_url)  # Construct authorization URL by combining the authorize_url with the oauth_token
    print("To authorize, please log in and click Authorize by browing the following URL:")
    print(auth_url)

    # Step 3: Get the verifier from the user
    verifier = input("\nEnter the verification code provided by Splitwise: ")  # User input for the temporary PIN from Splitwise (last code in the url)

    # Step 4: Exchange the request token and verifier for an access token
    oauth = OAuth1Session( # Creates a new OAuth1Session object using key, token, secret, and verifier
        consumer_key,  # Identifies your application
        client_secret=consumer_secret,  # Verifies the application's identity
        resource_owner_key=oauth_token,  # Temporary request token. Identifies the user during the exchange process
        resource_owner_secret=oauth_token_secret,  # Temporary request token secret
        verifier=verifier,  # Verification code that Splitwise gave to user
    )
    oauth_tokens = oauth.fetch_access_token(access_token_url)
    access_token = oauth_tokens.get("oauth_token")
    access_token_secret = oauth_tokens.get("oauth_token_secret")

    print("\nAccess Token obtained:")
    print(f"access_token: {access_token}")
    print(f"access_token_secret: {access_token_secret}\n")

    # Step 4:  Save the tokens to the settings file
    with open("settings.txt", 'w') as f: # Open a file and save the key, tokens and secrets
        f.write(f"consumer_key={consumer_key}\n")
        f.write(f"consumer_secret={consumer_secret}\n")
        f.write(f"oauth_token={oauth_token}\n")
        f.write(f"oauth_token_secret={oauth_token_secret}\n")
        f.write(f"access_token={access_token}\n")
        f.write(f"access_token_secret={access_token_secret}\n")
    print("Key, tokens and secrets are saved to settings.txt")
    sys.exit(0)

except Exception as e:
    print(f"Error during OAuth flow or saving tokens: {e}")

    
