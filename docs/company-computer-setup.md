# Company Computer Setup Guide

This guide explains how to access, run, modify, and push this project from another Windows computer.

## 1. Install Required Tools

Install Git and Python 3.12 on the company computer.

Check Git:

```powershell
git --version
```

Check Python:

```powershell
py -0p
```

The project expects Python 3.10 or newer. Python 3.12 is recommended.

## 2. Configure GitHub Access

### Option A: SSH

Create an SSH key if the computer does not already have one:

```powershell
ssh-keygen -t ed25519 -C "your_email@example.com"
```

Show the public key:

```powershell
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```

Add that public key in GitHub:

```text
GitHub -> Settings -> SSH and GPG keys -> New SSH key
```

Test SSH access:

```powershell
ssh -T git@github.com
```

### Option B: HTTPS

If the company network blocks SSH, use HTTPS instead:

```powershell
git clone https://github.com/Nitinool/Reception_demo.git
```

If the repository was already cloned with SSH, switch it to HTTPS:

```powershell
git remote set-url origin https://github.com/Nitinool/Reception_demo.git
```

## 3. Clone The Project

Using SSH:

```powershell
cd C:\Users\<your-user-name>\Documents
git clone git@github.com:Nitinool/Reception_demo.git
cd Reception_demo
```

Using HTTPS:

```powershell
cd C:\Users\<your-user-name>\Documents
git clone https://github.com/Nitinool/Reception_demo.git
cd Reception_demo
```

## 4. Run Tests

The project uses a `src` layout. In a new PowerShell session, set `PYTHONPATH` before running tests:

```powershell
$env:PYTHONPATH = "src"
py -3.12 -m unittest discover -s tests -v
```

The test suite should pass before making or pushing changes.

## 5. Run The Logger

Start recording:

```powershell
$env:PYTHONPATH = "src"
py -3.12 -m behavior_logger run --db data\behavior.db --poll-interval 1 --idle-threshold 60
```

Stop recording with:

```text
Ctrl+C
```

View recent events:

```powershell
py -3.12 -m behavior_logger tail --db data\behavior.db --limit 50
```

View one event type:

```powershell
py -3.12 -m behavior_logger tail --db data\behavior.db --type window.focus_started --limit 20
```

Export events as JSONL:

```powershell
py -3.12 -m behavior_logger export --db data\behavior.db --out exports\events.jsonl
```

Inspect the exported file:

```powershell
Get-Content exports\events.jsonl -TotalCount 5
```

## 6. Modify And Push Changes

Before changing files, pull the latest version:

```powershell
git pull
```

After editing, check changes:

```powershell
git status
```

Run tests:

```powershell
$env:PYTHONPATH = "src"
py -3.12 -m unittest discover -s tests -v
```

Commit and push:

```powershell
git add .
git commit -m "Describe your change"
git push
```

## 7. Important Notes

- Do not commit local behavior logs. The `data/` and `exports/` folders are ignored by Git because they may contain private window titles, webpage titles, filenames, and other sensitive activity data.
- If `tail` only shows `recording.started` and `recording.stopped`, the company computer may be blocking foreground-window access. Try running from a normal interactive PowerShell window.
- Some company security software may restrict Windows API calls used to read the foreground window and idle state.
- Each new PowerShell session needs `$env:PYTHONPATH = "src"` unless the package is installed in editable mode later.
- If SSH push fails because of network policy, switch the remote to HTTPS with `git remote set-url origin https://github.com/Nitinool/Reception_demo.git`.
