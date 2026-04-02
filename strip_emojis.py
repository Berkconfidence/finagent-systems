import re

def remove_emojis_and_fix_tone(content):
    # A broadly matching regex for emojis
    import emoji
    content = emoji.replace_emoji(content, replace='')
    
    # Fix some AI-like enthusiasm
    content = content.replace("Mükemmel, ", "")
    content = content.replace("İşte özet:\n", "")
    content = content.replace("✨ ", "")
    content = content.replace("🚀 ", "")
    content = content.replace("📚 ", "")
    content = content.replace("📂 ", "")
    content = content.replace("🗺️ ", "")
    content = content.replace("📄 ", "")
    content = content.replace("📋 ", "")
    content = content.replace("✅ ", "")
    content = content.replace("🔄 ", "")
    content = content.replace("🤖 ", "")
    content = content.replace("👁️ ", "")
    content = content.replace("📡 ", "")
    content = content.replace("🧑‍⚖️ ", "")
    content = content.replace("🧠 ", "")
    content = content.replace("📊 ", "")
    content = content.replace("🖥️ ", "")
    content = content.replace("🔧 ", "")
    content = content.replace("🏗️ ", "")
    content = content.replace("🎯 ", "")
    
    return content

