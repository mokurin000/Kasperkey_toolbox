' Kaspersky Toolbox by huawei_518
' ============================================
' DEOBFUSCATED VERSION
' Original: act.vbs
' All function/variable names have been renamed to meaningful equivalents
' ============================================
Option Explicit
On Error Resume Next

' --- WMI / COM Objects ---
Dim strComputer, wmiService, shell, fileSystem, registryProvider
Dim dataRoot, productType, productRoot, licenseType
Dim productKeyPath, licenseStoragePath, softwarePath32, softwarePath64, certificatesPath
Dim certBlobHex, licenseDataBinary, certDataSection, licenseFileData, certKeyName, objFile, objFile1, ID1
Dim runningProcesses, Items_d, Items_datc, Items_datd, filePath, byteCount, i
Dim exportFileName, fileMode, protectedSuffix, arrValues, arrValues1, strValues, strValue, strValue1
Dim productTypeHex, newCertBlobHex
Dim o, p, g, b, h, k, bt, bt1, L, n, r, RS, sl, Str, V

' --- Initialization ---
strComputer = "."
Set wmiService = GetObject("winmgmts:")
Set shell = WScript.CreateObject("WScript.Shell")
Set fileSystem = CreateObject("Scripting.FileSystemObject")
Set registryProvider = GetObject("winmgmts:{impersonationLevel=impersonate}!\\" & strComputer & "\root\default:StdRegProv")

Const HKLM = &H80000002
softwarePath32 = "SOFTWARE"
softwarePath64 = "SOFTWARE\Wow6432Node"
certificatesPath = "SOFTWARE\Microsoft\SystemCertificates\SPC\Certificates"

If Err.Number <> 0 Then WScript.Quit

' ====================================================================
' Function: LocateInstallation
' Purpose:  Enumerate Kaspersky registry subkeys to find the installed
'           product version by checking for avp.exe in ProductRoot.
' Parameters:
'   strKeyPath  - Base registry path (SOFTWARE or SOFTWARE\Wow6432Node)
'   pro         - Optional "\protected" suffix for enterprise versions
' Globals set:
'   productKeyPath     - Full path to version key
'   licenseStoragePath - Path to license storage (LicStrg or LicStorage)
'   productRoot        - Path containing avp.exe
' ====================================================================
Function LocateInstallation(strKeyPath, pro)
    On Error Resume Next
    Dim arrSubKeys, subkey
    arrSubKeys = ""
    subkey = ""
    registryProvider.EnumKey HKLM, strKeyPath & "\KasperskyLab" & pro, arrSubKeys
    For Each subkey In arrSubKeys
        Err.Clear
        productRoot = shell.RegRead("HKLM" & "\" & strKeyPath & "\KasperskyLab" & pro & "\" & subkey & "\environment\ProductRoot")
        If Err.Number = 0 And fileSystem.FileExists(productRoot & "\avp.exe") Then
            Err.Clear
            shell.RegRead("HKLM\" & strKeyPath & "\KasperskyLab" & pro & "\LicStrg\")
            If Err.Number = 0 Then licenseStoragePath = strKeyPath & "\KasperskyLab" & pro & "\LicStrg"
            Err.Clear
            shell.RegRead("HKLM\" & strKeyPath & "\KasperskyLab" & pro & "\LicStorage\")
            If Err.Number = 0 Then licenseStoragePath = strKeyPath & "\KasperskyLab" & pro & "\LicStorage"
            productKeyPath = strKeyPath & "\KasperskyLab" & pro & "\" & subkey
        End If
    Next
End Function

' --- Execute LocateInstallation with all 4 search paths ---
Err.Clear
productKeyPath = ""
protectedSuffix = "\protected"
Call LocateInstallation(softwarePath64, protectedSuffix)   ' 1. HKLM\SOFTWARE\WOW6432Node\KasperskyLab\protected
Call LocateInstallation(softwarePath32, protectedSuffix)   ' 2. HKLM\SOFTWARE\KasperskyLab\protected
protectedSuffix = ""                                       
Call LocateInstallation(softwarePath64, protectedSuffix)   ' 3. HKLM\SOFTWARE\WOW6432Node\KasperskyLab
Call LocateInstallation(softwarePath32, protectedSuffix)   ' 4. HKLM\SOFTWARE\KasperskyLab

' --- Read product environment details ---
dataRoot = ""
dataRoot = shell.RegRead("HKLM" & "\" & productKeyPath & "\environment\DataRoot")
productType = ""
productType = shell.RegRead("HKLM" & "\" & productKeyPath & "\environment\ProductType")
productRoot = ""
productRoot = shell.RegRead("HKLM" & "\" & productKeyPath & "\environment\ProductRoot")
licenseType = ""
licenseType = shell.RegRead("HKLM" & "\" & licenseStoragePath & "\kaspersky4win")
If licenseType <> "" Then
    productType = "kaspersky4win"
End If

' --- Encode productType to hex for certificate matching ---
productTypeHex = ""
For k = 1 To Len(productType)
    productTypeHex = productTypeHex & Hex(AscW(Mid(productType, k, 1))) & "00"
Next

Err.Clear
filePath = WScript.arguments(0)

' --- Iterate over all certificates in the SPC store ---
registryProvider.EnumKey HKLM, certificatesPath, arrValues 
For i = 0 To UBound(arrValues)
    p = 0
    p = shell.RegRead("HKLM" & "\" & certificatesPath & "\" & arrValues(i) & "\BlobCount")
    If p > 1 Then
        ' Multi-blob certificate: concatenate all blobs
        certBlobHex = ""
        For n = 0 To p - 1
            registryProvider.GetBinaryValue HKLM, certificatesPath & "\" & arrValues(i) & "\Blob" & n, "Blob", strValues
            For b = 0 To UBound(strValues)
                certBlobHex = certBlobHex & Right("0" & Hex(strValues(b)), 2)
            Next
        Next
    Else
        ' Single-blob certificate
        registryProvider.GetBinaryValue HKLM, certificatesPath & "\" & arrValues(i), "Blob", strValue
        certBlobHex = ""
        For b = 0 To UBound(strValue)
            certBlobHex = certBlobHex & Right("0" & Hex(strValue(b)), 2)
        Next
    End If

    ' Check if this certificate blob contains the product type we're looking for
    If InStr(certBlobHex, productTypeHex) > 0 And productTypeHex <> "" Then
        ' Check for duplicate product type in blob (indicates a license certificate)
        If InStr(Mid(certBlobHex, InStr(certBlobHex, productTypeHex) + Len(productTypeHex)), productTypeHex) > 0 Then
            certDataSection = Mid(certBlobHex, InStr(1, certBlobHex, "2000000001000000", 1))
            certKeyName = arrValues(i)
        End If
    End If

    ' --- LICENSE EXPORT: If no file argument, export license to desktop ---
    Err.Clear
    shell.RegRead("HKLM" & "\" & licenseStoragePath & "\")
    If Err.Number = 0 And filePath = "" Then
        exportFileName = shell.SpecialFolders("Desktop") & "\kaspersky_" & productType & ".dat"
        fileMode = 2
        registryProvider.GetBinaryValue HKLM, licenseStoragePath, productType, strValue1
        licenseDataBinary = ""
        For b = 0 To UBound(strValue1)
            licenseDataBinary = licenseDataBinary & Right("0" & Hex(strValue1(b)), 2)
        Next
        Set RS = CreateObject("ADODB.Recordset")
        L = Len(licenseDataBinary) / 2
        RS.Fields.Append "m", 205, L
        RS.Open
        RS.AddNew
        RS("m") = licenseDataBinary & ChrB(0)
        RS.Update
        licenseDataBinary = RS("m").GetChunk(L)
        With CreateObject("ADODB.Stream")
            .Mode = 3
            .Type = 1
            .Open
            .Write licenseDataBinary
            .SaveToFile exportFileName, fileMode
        End With
        WScript.Quit
    End If

    ' --- Size validation for kaspersky4win licenses ---
    Dim sizeCheckPassed, certDataLen, licenseDataLenPlus1
    sizeCheckPassed = False
    If licenseType <> "" Then
        certDataLen = Len(certBlobHex) / 2
        licenseDataLenPlus1 = UBound(licenseType) + 1
        If (certDataLen - licenseDataLenPlus1) > 400 And (certDataLen - licenseDataLenPlus1) < 600 Then
            sizeCheckPassed = True
        End If
    Else
        sizeCheckPassed = True
    End If

    ' --- LICENSE IMPORT / RESET: Process the license file ---
    If sizeCheckPassed And Right(Left(certBlobHex, 9), 7) = "A700000" And filePath <> "" Then
        Err.Clear
        
        ' Delete old certificate
        If p > 1 Then
            For n = 0 To p - 1
                shell.RegDelete("HKLM\" & certificatesPath & "\" & arrValues(i) & "\Blob" & n & "\")
            Next
        End If
        shell.RegDelete("HKLM\" & certificatesPath & "\" & arrValues(i) & "\")
        If Err.Number <> 0 Then
            WScript.Quit
        End If
        
        ' Set initialization mode
        Err.Clear
        shell.RegWrite "HKLM" & "\" & productKeyPath & "\settings\Ins_InitMode", "1", "REG_DWORD"
        If Err.Number <> 0 Then
            WScript.Quit
        End If
        
        ' Delete watchdog license info
        shell.RegDelete "HKLM" & "\" & productKeyPath & "\watchdog\LicenseInfo\"
        
        ' Delete license storage file
        fileSystem.DeleteFile(dataRoot & "\Data\stor_" & productType & ".bin")
        
        ' Read license file from disk
        With CreateObject("adodb.stream")
            .Type = 1
            .Open
            .LoadFromFile filePath
            Str = .read
            streamLength = LenB(Str)
        End With
        
        ' Decrypt license data (if .lic, subtract 18 from each byte)
        If ".lic" = Right(filePath, 4) Then
            For b = 1 To streamLength
                bt = AscB(MidB(Str, b, 1))
                objFile = objFile & Right("0" & Hex(bt - 18), 2)
            Next
        ElseIf ".dat" = Right(filePath, 4) Then
            For b = 1 To streamLength
                bt = AscB(MidB(Str, b, 1))
                objFile = objFile & Right("0" & Hex(bt), 2)
            Next
        Else
            WScript.Quit
        End If
        
        ' Extract license data starting with KLsw marker
        licenseFileData = Mid(objFile, InStr(1, objFile, "4B4C737700004B4C", 1))
        
        ' Convert hex string to byte array for registry
        ReDim Items_d(Len(licenseFileData) / 2 - 1)
        byteCount = 0
        For h = 1 To Len(licenseFileData) Step 2
            Items_d(byteCount) = "&H" & Mid(Trim(licenseFileData), h, 2)
            byteCount = byteCount + 1
        Next
        
        ' Write license data to registry storage
        registryProvider.SetBinaryValue HKLM, licenseStoragePath, productType, Items_d
        
        ' Reconstruct the certificate blob with header and write to SPC store
        If certKeyName <> "" And productType <> "" And certDataSection <> "" Then
            n = Len("000000" & Hex(byteCount))
            For b = 1 To 4
                o = o & Mid("000000" & Hex(byteCount), n - 1, 2)
                n = n - 2
            Next
            ' Build new certificate blob: header + license data + footer + original data section
            newCertBlobHex = "10A7000001000000" & o & Trim(licenseFileData) & Mid(certBlobHex, InStr(1, certBlobHex, "0300000001000000", 1), 64) & certDataSection
            
            ' Convert to byte array
            ReDim Items_datc(Len(newCertBlobHex) / 2 - 1)
            byteCount = 0
            For h = 1 To Len(newCertBlobHex) Step 2
                Items_datc(byteCount) = "&H" & Mid(newCertBlobHex, h, 2)
                byteCount = byteCount + 1
            Next
            
            ' Create certificate key and write blob
            registryProvider.CreateKey HKLM, certificatesPath & "\" & certKeyName
            If byteCount < 12289 Then
                ' Single blob (under 12KB limit)
                registryProvider.SetBinaryValue HKLM, certificatesPath & "\" & certKeyName, "Blob", Items_datc
            Else
                ' Multi-blob (split into 12KB chunks)
                shell.RegWrite "HKLM" & "\" & certificatesPath & "\" & certKeyName & "\BlobCount", byteCount \ 12288 + 1, "REG_DWORD"
                shell.RegWrite "HKLM" & "\" & certificatesPath & "\" & certKeyName & "\BlobLength", byteCount, "REG_DWORD"
                ReDim Items_datd(12287)
                r = 0
                For g = 0 To byteCount
                    Items_datd(r) = Items_datc(g)
                    r = r + 1
                    If r = 12288 Then
                        r = 0
                        registryProvider.CreateKey HKLM, certificatesPath & "\" & certKeyName & "\" & "Blob" & g \ 12288
                        registryProvider.SetBinaryValue HKLM, certificatesPath & "\" & certKeyName & "\" & "Blob" & g \ 12288, "Blob", Items_datd
                        If byteCount - g < 12288 Then ReDim Items_datd(byteCount - g - 2)
                    End If
                Next
                ' Write final chunk
                registryProvider.CreateKey HKLM, certificatesPath & "\" & certKeyName & "\" & "Blob" & g \ 12288
                registryProvider.SetBinaryValue HKLM, certificatesPath & "\" & certKeyName & "\" & "Blob" & g \ 12288, "Blob", Items_datd
            End If
        End If
    End If
Next

' --- Cleanup and restart if importing license ---
If filePath <> "" Then
    ' If we didn't find valid certificate data, clean up and exit
    If certKeyName = "" Or productType = "" Or certDataSection = "" Then
        registryProvider.EnumKey HKLM, certificatesPath, arrValues1
        For V = 0 To UBound(arrValues1)
            shell.RegDelete("HKLM\" & certificatesPath & "\" & arrValues1(V) & "\")
        Next
        WScript.Quit
    End If
    
    ' Kill avp.exe if running
    runningProcesses = ""
    Set ID1 = wmiService.ExecQuery("select * from win32_process where name like 'avp.exe'")
    For Each i In ID1
        runningProcesses = runningProcesses & i.Name
    Next
    If Len(runningProcesses) > 0 Then
        shell.Run "taskkill /f /im avp.exe", 0, True
    End If
    
    ' Restart avp.exe and avpui.exe
    shell.Run Chr(34) & productRoot & "\avp.exe" & Chr(34), 0, True
    shell.Run Chr(34) & productRoot & "\avpui.exe" & Chr(34), 0
End If

' --- Cleanup ---
Set wmiService = Nothing
Set shell = Nothing
Set fileSystem = Nothing
Set registryProvider = Nothing
WScript.Quit
