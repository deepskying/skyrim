unit StaffValidation;
var lines: TStringList;
    errors, checked: Integer;

procedure Validate(e: IInterface);
var i: Integer; message: string;
begin
  message := Check(e);
  if message <> '' then begin
    Inc(errors);
    lines.Add(FullPath(e) + ': ' + message);
  end;
  for i := 0 to ElementCount(e) - 1 do Validate(ElementByIndex(e, i));
end;

function Initialize: Integer;
var i, j: Integer; f, r: IInterface;
begin
  lines := TStringList.Create;
  errors := 0; checked := 0;
  for i := 0 to FileCount - 1 do begin
    f := FileByIndex(i);
    if GetFileName(f) = 'ArcaneArsenal.esp' then begin
      for j := 0 to RecordCount(f) - 1 do begin
        r := RecordByIndex(f, j);
        if ((GetLoadOrderFormID(r) and $FFFFFF) >= $B00) and
           ((GetLoadOrderFormID(r) and $FFFFFF) <= $B7F) then begin
          Validate(r); Inc(checked);
        end;
      end;
    end;
  end;
  lines.Insert(0, 'Checked=' + IntToStr(checked) + ' Errors=' + IntToStr(errors));
  lines.SaveToFile('C:\Users\linos\Desktop\github\skyrim\mods\arcane-arsenal\build\staff-xedit-report.txt');
  lines.Free;
  Result := 1;
end;
end.
