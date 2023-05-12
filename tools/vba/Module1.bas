Attribute VB_Name = "Module1"


Sub CheckIfFileExists()

    Dim rng As Range
    Dim cell As Range
    Dim folderPath As String
    Dim fileName As String
    Dim parts() As String
    Dim isError As Boolean

    ' Get the current folder path where the Excel document is located
    folderPath = ThisWorkbook.Path & "\output"

    ' Assuming values are in Column D, from row 2 to the last non-empty row
    Set rng = ThisWorkbook.Sheets("Documents").Range("D2:D" & ThisWorkbook.Sheets("Documents").Cells(Rows.Count, 4).End(xlUp).Row)
    
    For Each cell In rng
        isError = False
        
        ' Split the cell value by the "\" character
        parts = Split(cell.Value, "\")

        ' Get the last item from the array
        On Error Resume Next
        fileName = parts(UBound(parts))
        If Err.Number <> 0 Then
            Err.Clear
            ' Set isError to True if an error occurs
            isError = True
        End If
        On Error GoTo 0

        ' Skip to next iteration if an error occurred
        If isError Then GoTo NextIteration

        If Dir(folderPath & "\" & fileName) <> "" Then
            cell.Offset(0, 8).Value = "File Exists" ' Writes the result in column L of the same row
        Else
            cell.Offset(0, 8).Value = "File Does Not Exist" ' Writes the result in column L of the same row
        End If

NextIteration:
    Next cell

End Sub
