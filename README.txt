UTM_Classroom recovery README
=============================
Generated: 2026-07-25

This tree was rebuilt after accidental deletion of UTM_Classroom.
Sources: Cursor Local History (Jul 2026 snapshots) + copied shared EA bin/Misc files.

RESTORED FROM CURSOR HISTORY
----------------------------
bin/utm_coordinate_wizard.py
bin/student_pack.py
bin/seal_geoid.py
bin/tools/build_edition_exe.py
bin/tools/build_lecturer_package.py
bin/tools/generate_branding.py
bin/tools/_launch_check_utm.py
bin/branding/README.txt
bat/5_UTM_Lecturer_Dev.bat
bat/5_EA_Coordinate_Wizard_Lecturer_Dev.bat (stub — points to correct launchers)
bat/8_EA_Build_Student_EXE.bat
bat/8_UTM_Build_Lecturer_EXE.bat
bat/9_EA_Build_Lecturer_Package.bat
README_FOR_LECTURER.txt
Misc/Malaysia.xml (+ copy at classroom root Malaysia.xml)

COPIED FROM EA_ASCII (shared runtime — not in UTM-only history)
---------------------------------------------------------------
bin/app_paths.py, ui_theme.py, win_boot.py, datum_transform.py, malaysia_zones.py
bin/geoid_vault.py, param_vault.py, cassini_converter.py, seal_malaysia.py
bin/wgeoid04.gff, WGeoid04.gsf
Misc/Malaysia.eap

GENERATED DURING RECOVERY
-------------------------
Misc/Malaysia.utm (sealed from Misc/Malaysia.xml via bin/seal_malaysia.py --utm)
Reference script: EA_ASCII/bin/tools/_split_utm_classroom.py (reconstructed; not from history)

BAT PATCHES
-----------
All launchers under bat/ set:
  ROOT=%~dp0..\..     (EA_ASCII)
  UTM=%~dp0..         (this folder)
  PYTHONPATH=%UTM%\bin;%ROOT%\bin
Paths use %UTM%\bin and %UTM%\exe. Python installer uses %ROOT%\bin\install_python_latest.bat.

BRANDING (2026-07-25)
---------------------
Regenerated via bin/tools/generate_branding.py after downloading Wikimedia Commons
UTM-LOGO.png / UTM-LOGO-FULL.png into bin/branding/assets/ (User-Agent required; bare
urllib previously got HTTP 403). Lecturer + student logo.png / icon.ico / icon_win.png
are present under bin/branding/lecturer/ and bin/branding/student/.

STILL MISSING / INCOMPLETE
--------------------------
- exe/UTM_Coordinate_Wizard_Lecturer.exe and exe/UTM_Coordinate_Wizard_Student.exe (not rebuilt yet)
- dist/UTM_Coordinate_Wizard_Lecturer/ package output (run bat/9 after building exe)
- Sealed geoid *.utm beside bin (run seal_geoid.py before student exe build)
- Original _split_utm_classroom.py body from Jul 10 (only reconstructed MOVES list)
- bin/build_edition_exe.py and bin/generate_branding.py at EA bin root (pre-split copies; tools/ versions restored)
- bin/tools/ea_coordinate_wizard_xml_edition.py (seen in Cursor history; not restored — optional)

HOW TO USE
----------
Lecturer dev (Python):
  UTM_Classroom\bat\5_UTM_Lecturer_Dev.bat

Build lecturer exe:
  UTM_Classroom\bat\8_UTM_Build_Lecturer_EXE.bat
  (Branding assets already regenerated; rebuild if logos change)

Build student exe:
  UTM_Classroom\bat\8_EA_Build_Student_EXE.bat

Full tree listing: EA_ASCII\_utm_restored_tree.txt

Smoke test performed: import utm_coordinate_wizard OK with EA_EDITION=lecturer.
