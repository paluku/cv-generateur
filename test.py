import requests

CLIENT_ID = "PAR_cvgenerateur_640b5de026cb7fd7b47df3fbef12ed968b6e59b34cf6f7dba2569a251bbb52bf"
CLIENT_SECRET = "406289fc3e49d7e6193a39fef60c23eca78efa6faca3abad2c9e9072a2fbaab8"

url = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"

data = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": "api_offresdemploiv2 o2dsoffre"
}

response = requests.post(
    url,
    data=data,
    headers={
        "Content-Type": "application/x-www-form-urlencoded"
    },
    timeout=15
)

print("HTTP :", response.status_code)
print("Réponse :", response.text)