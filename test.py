import google.generativeai as genai
genai.configure(api_key="AIzaSyAUPnxqbo9tZKzG_jQFES7bZg8A1og4dM8")
for m in genai.list_models():
    print(m.name)