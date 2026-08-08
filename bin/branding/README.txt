BRANDING
=======

Lecturer edition uses Universiti Teknologi Malaysia (UTM) artwork automatically.

  bin/branding/assets/
    utm_emblem.png   — UTM circular seal (icon source)
    utm_full.png     — UTM full signature (header logo source)

  bin/branding/lecturer/
    logo.png         — generated header banner (UTM + navy + gold bar)
    icon.ico         — rounded-frame icon with UTM emblem (matches EA icon style)

  bin/branding/student/
    logo.png / icon.ico — student edition placeholders

Regenerate after changing source artwork:

  python bin\tools\generate_branding.py

Then rebuild:

  9_EA_Build_Lecturer_Package.bat
