@echo off

rem เปลี่ยนไปยังไดเรกทอรี่ที่เก็บไฟล์ batch file
cd %~dp0

rem แสดงตำแหน่งปัจจุบันหลังเปลี่ยนไดเรกทอรี่
echo Current directory after change: %CD%

rem เรียกใช้ active.bat เพื่อ activate Python environment
call ./env/Scripts/activate.bat"

rem รอ 1 วินาทีหลังจาก activate environment
timeout /t 1

python main.py

rem บันทึกค่า exit code หลังรัน Python script
set exitcode=%errorlevel%

rem Deactivate Python environment (if script exited with error)
if %exitcode% neq 0 (
  call ./env/Scripts/deactivate.bat"
)