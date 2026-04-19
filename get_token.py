import requests

APP_ID     = "982991217577298"
APP_SECRET = "a9b3aaf1f2e1ee0b92c011b1c4293433"   # <- remplace
TOKEN      = "EAANZBBnpXTVIBRK4qg29ZCl6pOoGDfyhFAr5J3weW49m0iwjsKCY7D8jbtQrDZBJlco30ZC49HDtIKaY9gQWkwN6hQfgDMTOWjVBwtCPPIm2uvbsdU5vYLse3bSKGsWVd0tdMsfK3ILcpKmICw2yWrbNmPNtcSVbHYnqEFS3YbsyKlqraesb9cNErGgnXV3ZCJ5IoaXSbFNW6eiLmK5SXH4dTJ08L2cLSoZAaqc7jpWHu1UhscnjaF0I9WAlj01fiL5kfdgoTumbn7KbZC62v8hNxCW"  # <- remplace par token frais de l'Explorateur

r = requests.get(
    "https://graph.facebook.com/v19.0/oauth/access_token",
    params={
        "grant_type":        "fb_exchange_token",
        "client_id":         APP_ID,
        "client_secret":     APP_SECRET,
        "fb_exchange_token": TOKEN,
    }
)
print(r.json())
