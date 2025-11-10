import os

print("📁 Checking pages folder...")
print(f"Current directory: {os.getcwd()}")

if os.path.exists('pages'):
    print("\n✅ 'pages' folder exists!")
    files = os.listdir('pages')
    print(f"\n📄 Files in pages folder ({len(files)} files):")
    for file in sorted(files):
        print(f"  - {file}")
else:
    print("\n❌ 'pages' folder NOT found!")