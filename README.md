# SFTP Stress Test Tool

Tool for testing the performance and reliability of SFTP servers under different load conditions.

## Overview

The SFTP Stress Test Tool allows users to benchmark and stress test SFTP servers by simulating multiple simultaneous connections and file transfers.

The tool helps determine performance bottlenecks, connection limits and overall server stability.

## Download

Compiled Windows executable is located at:

![alt text](_internal/docs/binary_exe.png)

Download `7z` file `SFTPTestTool.7z` and unzip it in a folder.

![alt text](_internal/docs/exe.png)
___

## Functions

### SFTP configuration


- Connection to any SFTP server with standard authentication

- Customizable port selection (default: 22)

- Specification of the directory path for file transfers

### Test parameters

- Selection of specific test files for transfer

- Configuration of the number of simultaneous connections (1-100)

- Possible activation of multiple file transfers simultaneously


### Additional tools

- Integrated dummy file generator for creating test files

- Autofill function for frequently used configurations, expandable under “Settings”

## Usage

- Enter details of the SFTP server (host, port, directory, user name, password)

- Select a test file or create one or more dummy files (optional)

- Configure test parameters (simultaneous connections, multiple file transfers)

- Click on “Run SFTP Stress Test” to start the process


## Screenshot

![alt text](_internal/docs/pt1.png)
