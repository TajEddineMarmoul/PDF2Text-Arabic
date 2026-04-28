import re

text = """
واملصوغات
باملادة
فاملمارسين
كاملعتاد
"""

def repair_token(match):
    token = match.group(0)
    
    if len(token) >= 4:
        token = re.sub(r"^([وفبك]?)امل(?=[ء-ي])", r"\1الم", token)
        
    return token

fixed = re.sub(r"[ء-ي]{2,}", repair_token, text)
print(fixed)
