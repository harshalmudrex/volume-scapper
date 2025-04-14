import base64

# Read the JSON file
with open("volume-scrapper.json", "rb") as json_file:
    encoded_credentials = base64.b64encode(json_file.read()).decode("utf-8")

# Write the encoded string to a file
with open("encoded_credentials.txt", "w") as output_file:
    output_file.write(encoded_credentials)

print("Base64 encoding complete. Check encoded_credentials.txt.")
