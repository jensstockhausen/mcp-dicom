@echo off
setlocal

set "workspace_root=%~dp0"
set "skill_directory=%workspace_root%.github\skills\dicom-metadata-skill"
set "skill_source=%workspace_root%skill.md"
set "skill_destination=%skill_directory%\skill.md"

if not exist "%skill_directory%" mkdir "%skill_directory%"
if errorlevel 1 exit /b 1

copy /Y "%skill_source%" "%skill_destination%" >nul
exit /b %errorlevel%