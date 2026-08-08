UTM COORDINATE WIZARD — LECTURER EDITION
======================================

Thank you for your guidance on how Malaysian coordinate conversion works —
this lecturer edition is built with you and your students in mind.
From UTM Student, For UTM Student.

CONTENTS
  UTM_Coordinate_Wizard_Lecturer.exe   Your copy (UTM logo/icon)
  Malaysia.xml                         Support file — keep in the same folder as the .exe
  README_FOR_LECTURER.txt              This file

  Geoid grid and student template are embedded in the lecturer .exe
  (no separate WGEOID files needed beside this folder).

RUN
  Double-click UTM_Coordinate_Wizard_Lecturer.exe (no Python needed).
  Keep Malaysia.xml in the same folder as the .exe.

TABS
  Convert     — single-point conversion; Export KML/KMZ after Convert
  Batch       — many points: paste from Excel, Import TXT/CSV/Excel,
                Convert All, export Excel / CSV / KML/KMZ
  Geoid       — WGeoid04 undulation lookup
  Distribute  — package the student edition for your class
  Help        — step-by-step guide for every tab

BATCH TIPS
  • Paste coordinate columns only — values go to Northing/Easting (or Lat/Lon),
    not the Name column. Include a name column only if your sheet has point names.
  • Lat/Lon rows auto-detect which value is latitude (|value| ≤ 90°).
  • For grid coordinates, choose  Paste column order  (N then E or E then N)
    above the table, or use a header row (Northing, Easting, …).
  • When  From  is UTM, set Zone and Hemisphere above the table (defaults for
    all rows); you can still override per row in the table.
  • Row numbers (#) are automatic; Name is optional.

DISTRIBUTE TO STUDENTS
  1. Open the app → tab  Distribute
  2. Optionally type your name — it appears as
     "From your lecturer <your name>" in the student README
  3. Click  Export Student ZIP…  and save
  4. Share the zip — students double-click the .exe inside; no extra files
     (student zip = .exe + README only; geoid is inside the student .exe)

  Optional:  Generate class test coordinates…  for practice sets.

CUSTOM LOGO / ICON (developer rebuild only)
  Replace files in bin/branding/lecturer/ and bin/branding/student/
  then run 9_EA_Build_Lecturer_Package.bat again.

With gratitude,
Firdaus Shah / Ezam & Associates
