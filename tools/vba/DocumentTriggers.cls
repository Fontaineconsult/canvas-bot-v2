Private Sub Worksheet_Change(ByVal Target As Range)

    ' Check if the changed cell is in column K (11)
    If Target.Column = 11 Then
        CheckIfFileExists
    End If

End Sub
