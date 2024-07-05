@echo off

rem เปลี่ยนไปยังไดเรกทอรี่ที่เก็บไฟล์ batch file
cd %~dp0

rem แสดงตำแหน่งปัจจุบันหลังเปลี่ยนไดเรกทอรี่
echo Current directory after change: %CD%


rem ตรวจสอบว่ามี virtual environment อยู่แล้วหรือไม่
if not exist "env" (
    echo Creating virtual environment...
    python -m venv env
) else (
    echo Virtual environment already exists.
)

rem Activate virtual environment
call ./env/Scripts/activate.bat

rem ติดตั้ง dependencies จาก requirement.txt
echo Installing requirement...
pip install -r requirement.txt

rem รัน Python script
python main.py

rem บันทึกค่า exit code หลังรัน Python script
set exitcode=%errorlevel%

rem Deactivate Python environment (if script exited with error)
if %exitcode% neq 0 (
    call ./env/Scripts/deactivate.bat
)
