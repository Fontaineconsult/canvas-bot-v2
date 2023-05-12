Private Sub Worksheet_Change(ByVal Target As Range)

    ' Check if the changed cell is in column K (10)
    If Target.Column = 10 Then
        CheckIfFileExists
    End If

End Sub
