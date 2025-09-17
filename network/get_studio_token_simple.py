import requests
import webbrowser
import os

def get_canvas_studio_access_token_only(client_id, client_secret, auth_url, token_url, redirect_uri):
    """
    Performs Canvas Studio OAuth flow and returns access token.

    :param client_id: OAuth client ID
    :param client_secret: OAuth client secret
    :param auth_url: Authorization endpoint URL
    :param token_url: Token exchange endpoint URL
    :param redirect_uri: Registered callback URI
    :return: access_token or None
    """

    # Step 1: Generate authorization URL
    auth_params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_uri
    }
    authorization_redirect_url = auth_url + '?' + '&'.join([f"{k}={v}" for k, v in auth_params.items()])
    print(f"Visit this URL to authorize: {authorization_redirect_url}")
    webbrowser.open(authorization_redirect_url)

    # Step 2: User manually pastes auth code from redirect
    auth_code = input("Paste the authorization code from the URL after login: ").strip()

    # Step 3: Exchange code for access token
    token_payload = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'client_secret': client_secret
    }

    response = requests.post(token_url, data=token_payload)

    if response.status_code == 200:
        token_data = response.json()
        return token_data['access_token']  # You can also return the full token_data if needed
    else:
        print("Error retrieving access token:", response.text)
        return None


