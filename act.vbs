'Kaspersky Toolbox by huawei_518
Option Explicit
On Error Resume Next

Dim strComputer, GOj, Wsh, fso, oReg
Dim Datad_a, Datad_b, Datad_c, Datad_d
Dim Location, Location1, strKeyPath_1, strKeyPath_2, strKey
Dim datd, datdn, datd1, datdg, Itemss, objFile, objFile1, ID1
Dim Arrtr, Items_d, Items_datc, Items_datd, fpcth, fcy, i
Dim Fname, F, protected, arrValues, strValues, strValue, strValue1
Dim o, p, g, b, h, k, bt, bt1, L, n, r, RS, sl, Str

strComputer = "."
Set GOj = GetObject("winmgmts:")
Set Wsh = WScript.CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
Set oReg = GetObject("winmgmts:{impersonationLevel=impersonate}!\\" & strComputer & "\root\default:StdRegProv")

Const HKLM = &H80000002
strKeyPath_1 = "SOFTWARE"
strKeyPath_2 = "SOFTWARE\Wow6432Node"
strKey = "SOFTWARE\Microsoft\SystemCertificates\SPC\Certificates"

If Err.Number <> 0 Then WScript.Quit

Function LiRu(strKeyPath, pro)
    On Error Resume Next
    Dim arrSubKeys, subkey
    arrSubKeys = ""
    subkey = ""
    oReg.EnumKey HKLM, strKeyPath & "\KasperskyLab" & pro, arrSubKeys
    For Each subkey In arrSubKeys
        Err.Clear
        Datad_c = Wsh.RegRead("HKLM" & "\" & strKeyPath & "\KasperskyLab" & pro & "\" & subkey & "\environment\ProductRoot")
        If Err.Number = 0 And fso.FileExists(Datad_c & "\avp.exe") Then
            Err.Clear
            Wsh.RegRead("HKLM\" & strKeyPath & "\KasperskyLab" & pro & "\LicStrg\")
            If Err.Number = 0 Then Location1 = strKeyPath & "\KasperskyLab" & pro & "\LicStrg"
            Err.Clear
            Wsh.RegRead("HKLM\" & strKeyPath & "\KasperskyLab" & pro & "\LicStorage\")
            If Err.Number = 0 Then Location1 = strKeyPath & "\KasperskyLab" & pro & "\LicStorage"
            Location = strKeyPath & "\KasperskyLab" & pro & "\" & subkey
        End If
    Next
End Function

Err.Clear
Location = ""
protected = "\protected"
Call LiRu(strKeyPath_2, protected)
Call LiRu(strKeyPath_1, protected)
protected = ""
Call LiRu(strKeyPath_2, protected)
Call LiRu(strKeyPath_1, protected)

Datad_a = ""
Datad_a = Wsh.RegRead("HKLM" & "\" & Location & "\environment\DataRoot")
Datad_b = ""
Datad_b = Wsh.RegRead("HKLM" & "\" & Location & "\environment\ProductType")
Datad_c = ""
Datad_c = Wsh.RegRead("HKLM" & "\" & Location & "\environment\ProductRoot")
Datad_d = ""
Datad_d = Wsh.RegRead("HKLM" & "\" & Location1 & "\kaspersky4win")
If Datad_d <> "" Then
    Datad_b = "kaspersky4win"
End If

bt1 = ""
For k = 1 To Len(Datad_b)
    bt1 = bt1 & Hex(AscW(Mid(Datad_b, k, 1))) & "00"
Next

Err.Clear
fpcth = WScript.arguments(0)

oReg.EnumKey HKLM, strKey, arrValues 
For i = 0 To UBound(arrValues)
    p = 0
    p = Wsh.RegRead("HKLM" & "\" & strKey & "\" & arrValues(i) & "\BlobCount")
    If p > 1 Then
        datd = ""
        For n = 0 To p - 1
            oReg.GetBinaryValue HKLM, strKey & "\" & arrValues(i) & "\Blob" & n, "Blob", strValues
            For b = 0 To UBound(strValues)
                datd = datd & Right("0" & Hex(strValues(b)), 2)
            Next
        Next
    Else
        oReg.GetBinaryValue HKLM, strKey & "\" & arrValues(i), "Blob", strValue
        datd = ""
        For b = 0 To UBound(strValue)
            datd = datd & Right("0" & Hex(strValue(b)), 2)
        Next
    End If

    If InStr(datd, bt1) > 0 And bt1 <> "" Then
        If InStr(Mid(datd, InStr(datd, bt1) + Len(bt1)), bt1) > 0 Then
            datd1 = Mid(datd, InStr(1, datd, "2000000001000000", 1))
            Itemss = arrValues(i)
        End If
    End If

    Err.Clear
    Wsh.RegRead("HKLM" & "\" & Location1 & "\")
    If Err.Number = 0 And fpcth = "" Then
        Fname = Wsh.SpecialFolders("Desktop") & "\kaspersky_" & Datad_b & ".dat"
        F = 2
        oReg.GetBinaryValue HKLM, Location1, Datad_b, strValue1
        datdn = ""
        For b = 0 To UBound(strValue1)
            datdn = datdn & Right("0" & Hex(strValue1(b)), 2)
        Next
        Set RS = CreateObject("ADODB.Recordset")
        L = Len(datdn) / 2
        RS.Fields.Append "m", 205, L
        RS.Open
        RS.AddNew
        RS("m") = datdn & ChrB(0)
        RS.Update
        datdn = RS("m").GetChunk(L)
        With CreateObject("ADODB.Stream")
            .Mode = 3
            .Type = 1
            .Open
            .Write datdn
            .SaveToFile Fname, F
        End With
        WScript.Quit
    End If

    Dim allow, my_i, my_j
    allow = False
    If Datad_d <> "" Then
        my_i = Len(datd) / 2
        my_j = UBound(Datad_d) + 1
        If (my_i - my_j) > 400 And (my_i - my_j) < 600 Then
            allow = True
        End If
    Else
        allow = True
    End If

    If allow And Right(Left(datd, 9), 7) = "A700000" And fpcth <> "" Then
        Err.Clear
        If p > 1 Then
            For n = 0 To p - 1
                Wsh.RegDelete("HKLM\" & strKey & "\" & arrValues(i) & "\Blob" & n & "\")
            Next
        End If
        Wsh.RegDelete("HKLM\" & strKey & "\" & arrValues(i) & "\")
        If Err.Number <> 0 Then
            WScript.Quit
        End If
        Err.Clear
        Wsh.RegWrite "HKLM" & "\" & Location & "\settings\Ins_InitMode", "1", "REG_DWORD"
        If Err.Number <> 0 Then
            WScript.Quit
        End If
        Wsh.RegDelete "HKLM" & "\" & Location & "\watchdog\LicenseInfo\"
        fso.DeleteFile(Datad_a & "\Data\stor_" & Datad_b & ".bin")
        With CreateObject("adodb.stream")
            .Type = 1
            .Open
            .LoadFromFile fpcth
            Str = .read
            sl = LenB(Str)
        End With
        If ".lic" = Right(fpcth, 4) Then
            For b = 1 To sl
                bt = AscB(MidB(Str, b, 1))
                objFile = objFile & Right("0" & Hex(bt - 18), 2)
            Next
        ElseIf ".dat" = Right(fpcth, 4) Then
            For b = 1 To sl
                bt = AscB(MidB(Str, b, 1))
                objFile = objFile & Right("0" & Hex(bt), 2)
            Next
        Else
            WScript.Quit
        End If
        datdg = Mid(objFile, InStr(1, objFile, "4B4C737700004B4C", 1))
        ReDim Items_d(Len(datdg) / 2 - 1)
        fcy = 0
        For h = 1 To Len(datdg) Step 2
            Items_d(fcy) = "&H" & Mid(Trim(datdg), h, 2)
            fcy = fcy + 1
        Next
        oReg.SetBinaryValue HKLM, Location1, Datad_b, Items_d
        If Itemss <> "" And Datad_b <> "" And datd1 <> "" Then
            n = Len("000000" & Hex(fcy))
            For b = 1 To 4
                o = o & Mid("000000" & Hex(fcy), n - 1, 2)
                n = n - 2
            Next
            objFile1 = "10A7000001000000" & o & Trim(datdg) & Mid(datd, InStr(1, datd, "0300000001000000", 1), 64) & datd1
            ReDim Items_datc(Len(objFile1) / 2 - 1)
            fcy = 0
            For h = 1 To Len(objFile1) Step 2
                Items_datc(fcy) = "&H" & Mid(objFile1, h, 2)
                fcy = fcy + 1
            Next
            oReg.CreateKey HKLM, strKey & "\" & Itemss
            If fcy < 12289 Then
                oReg.SetBinaryValue HKLM, strKey & "\" & Itemss, "Blob", Items_datc
            Else
                Wsh.RegWrite "HKLM" & "\" & strKey & "\" & Itemss & "\BlobCount", fcy \ 12288 + 1, "REG_DWORD"
                Wsh.RegWrite "HKLM" & "\" & strKey & "\" & Itemss & "\BlobLength", fcy, "REG_DWORD"
                ReDim Items_datd(12287)
                r = 0
                For g = 0 To fcy
                    Items_datd(r) = Items_datc(g)
                    r = r + 1
                    If r = 12288 Then
                        r = 0
                        oReg.CreateKey HKLM, strKey & "\" & Itemss & "\" & "Blob" & g \ 12288
                        oReg.SetBinaryValue HKLM, strKey & "\" & Itemss & "\" & "Blob" & g \ 12288, "Blob", Items_datd
                        If fcy - g < 12288 Then ReDim Items_datd(fcy - g - 2)
                    End If
                Next
                oReg.CreateKey HKLM, strKey & "\" & Itemss & "\" & "Blob" & g \ 12288
                oReg.SetBinaryValue HKLM, strKey & "\" & Itemss & "\" & "Blob" & g \ 12288, "Blob", Items_datd
            End If
        End If
    End If
Next

If fpcth <> "" Then
    If Itemss = "" Or Datad_b = "" Or datd1 = "" Then
        oReg.EnumKey HKLM, strKey, arrValues1
        For V = 0 To UBound(arrValues1)
            Wsh.RegDelete("HKLM\" & strKey & "\" & arrValues1(V) & "\")
        Next
        WScript.Quit
    End If
    Arrtr = ""
    Set ID1 = GOj.ExecQuery("select * from win32_process where name like 'avp.exe'")
    For Each i In ID1
        Arrtr = Arrtr & i.Name
    Next
    If Len(Arrtr) > 0 Then
        Wsh.Run "taskkill /f /im avp.exe", 0, True
    End If
    Wsh.Run Chr(34) & Datad_c & "\avp.exe" & Chr(34), 0, True
    Wsh.Run Chr(34) & Datad_c & "\avpui.exe" & Chr(34), 0
End If

Set GOj = Nothing
Set Wsh = Nothing
Set fso = Nothing
Set oReg = Nothing
WScript.Quit
[file content end]