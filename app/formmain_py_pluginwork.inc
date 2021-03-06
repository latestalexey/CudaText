{$ifdef nn}begin end;{$endif}

procedure TfmMain.DoPyStringToEvents(const AEventStr: string;
  out AEvents: TAppPyEvents;
  out AEventsPrior: TAppPyEventsPrior;
  out AEventsLazy: TAppPyEventsLazy);
var
  str, strItem: string;
  event: TAppPyEvent;
  nPrior: byte;
  bLazy: boolean;
begin
  AEvents:= [];
  FillChar(AEventsPrior, SizeOf(AEventsPrior), 0);
  FillChar(AEventsLazy, SizeOf(AEventsLazy), 0);
  str:= AEventStr;
  repeat
    strItem:= SGetItem(str);
    if strItem='' then Break;

    nPrior:= 0;
    while SEndsWith(strItem, '+') do
    begin
      Inc(nPrior);
      SetLength(strItem, Length(strItem)-1);
    end;

    bLazy:= false;
    if SEndsWith(strItem, '~') then
    begin
      bLazy:= true;
      SetLength(strItem, Length(strItem)-1);
    end;

    for event in TAppPyEvent do
      if strItem=cAppPyEvent[event] then
      begin
        Include(AEvents, event);
        AEventsPrior[event]:= nPrior;
        AEventsLazy[event]:= bLazy;
        Break
      end;
  until false;
end;


procedure TfmMain.DoOps_LoadPlugins;
var
  list: TStringlist;
  SItem, fn: string;
  i: integer;
begin
  //commands: don't clear all, leave items from Api
  for i:= High(AppPluginsCommand) downto Low(AppPluginsCommand) do
    if (AppPluginsCommand[i].ItemModule<>'') and (not AppPluginsCommand[i].ItemFromApi) then
      CommandPlugins_DeleteItem(i);
  //events: clear all
  FillChar(AppPluginsEvent, SizeOf(AppPluginsEvent), 0);

  list:= TStringlist.Create;
  try
    FindAllDirectories(list, GetAppPath(cDirPy), false);
    list.Sort;
    for SItem in list do
    begin
      fn:= SItem+DirectorySeparator+'install.inf';
      if FileExists(fn) then
        DoOps_LoadPluginFromInf(fn);
    end;
  finally
    FreeAndNil(list);
  end;

  UpdateKeymapDynamicItems;
end;


procedure TfmMain.DoOps_LoadPluginFromInf(const fn_inf: string);
var
  ini: TIniFile;
  sections: TStringList;
  ini_section,
  dir_inf, s_section, s_caption, s_module, s_method, s_lexers,
  s_events, s_keys, s_inmenu, s_icon: string;
  cnt: integer;
begin
  ini:= TIniFile.Create(fn_inf);
  sections:= TStringList.Create;

  try
    dir_inf:= ExtractFileDir(fn_inf);
    s_module:= ExtractFileName(dir_inf);
    ini.ReadSections(sections);

    for s_section in sections do
    begin
      if not SRegexMatchesString(s_section, 'sidebar\d+', true) then Continue;

      s_caption:= ini.ReadString(s_section, 'hint', '');
      if s_caption='' then Continue;

      s_icon:= ini.ReadString(s_section, 'icon', '');
      if s_icon='' then Continue;
      s_icon:= StringReplace(s_icon, '{dir}', dir_inf, []);
      {$ifdef windows}
      s_icon:= StringReplace(s_icon, '/', '\', [rfReplaceAll]);
      {$endif}

      s_method:= ini.ReadString(s_section, 'method', '');
      if s_method='' then Continue;

      DoSidebar_AddTab_Empty(
        s_caption,
        DoSidebar_FilenameToImageIndex(s_caption, s_icon),
        s_module,
        s_method
        );
    end;

    for ini_section in sections do
    begin
      if not SRegexMatchesString(ini_section, 'item\d+', true) then Continue;

      s_section:= ini.ReadString(ini_section, 'section', '');
      s_caption:= ini.ReadString(ini_section, 'caption', '');
      s_method:= ini.ReadString(ini_section, 'method', '');
      //s_hotkey:= ini.ReadString(ini_section, 'hotkey', '');

      s_lexers:= ini.ReadString(ini_section, 'lexers', '');
      if SBeginsWith(s_lexers, '$') then //var $name defined in [info]
        s_lexers:= ini.ReadString('info', s_lexers, '');

      s_events:= ini.ReadString(ini_section, 'events', '');
      s_keys:= ini.ReadString(ini_section, 'keys', '');
      s_inmenu:= ini.ReadString(ini_section, 'menu', '');

      if s_section='commands' then
      begin
        if s_caption='' then Continue;
        if s_method='' then Continue;

        cnt:= 0;
        while AppPluginsCommand[cnt].ItemModule<>'' do Inc(cnt);
        if cnt>=High(AppPluginsCommand) then Break;

        AppPluginsCommand[cnt].ItemModule:= s_module;
        AppPluginsCommand[cnt].ItemProc:= s_method;
        AppPluginsCommand[cnt].ItemProcParam:= '';
        AppPluginsCommand[cnt].ItemCaption:= s_caption;
        AppPluginsCommand[cnt].ItemLexers:= s_lexers;
        AppPluginsCommand[cnt].ItemInMenu:= s_inmenu;
      end;

      if s_section='events' then
      begin
        if s_events='' then Continue;

        cnt:= 0;
        while AppPluginsEvent[cnt].ItemModule<>'' do Inc(cnt);
        if cnt>=High(AppPluginsEvent) then Break;

        AppPluginsEvent[cnt].ItemModule:= s_module;
        DoPyStringToEvents(s_events,
          AppPluginsEvent[cnt].ItemEvents,
          AppPluginsEvent[cnt].ItemEventsPrior,
          AppPluginsEvent[cnt].ItemEventsLazy
          );
        AppPluginsEvent[cnt].ItemLexers:= s_lexers;
        AppPluginsEvent[cnt].ItemKeys:= s_keys;
      end;
    end;
  finally
    FreeAndNil(sections);
    FreeAndNil(ini);
  end;
end;


procedure TfmMain.DoOps_ShowEventPlugins;
var
  i: integer;
  s, s2: string;
  ev: TAppPyEvent;
begin
  exit;////////

  s:= '';
  for i:= 0 to 100 do
    with AppPluginsEvent[i] do
    begin
      if ItemModule='' then Break;
      s2:= '';
      for ev in TAppPyEvent do
        if ev in ItemEvents then
          s2:= s2+'/'+cAppPyEvent[ev];

      s:= s+#13+
        'module: '+ItemModule+#13+
        'lexers: "'+ItemLexers+'"'#13+
        'keys: "'+ItemKeys+'"'#13+
        'events: '+s2+#13;
    end;
  Showmessage(s);
end;


procedure TfmMain.DoOps_AddPluginMenuItem(ACaption: string; ASubMenu: TMenuItem; ATag: integer);
var
  mi: TMenuItem;
  strItem: string;
  idx, NInsert: integer;
  bRoot: boolean;
begin
  mi:= nil;
  bRoot:= true;

  //need to parse caption and create subitems, separated with '\'
  repeat
    strItem:= SGetItem(ACaption, '\');
    if strItem='' then Break;
    if strItem='-' then
      idx:= -1
    else
      idx:= ASubMenu.IndexOfCaption(strItem);
    if idx<0 then
    begin
      mi:= TMenuItem.Create(Self);
      mi.Caption:= strItem;

      if bRoot then
      begin
        NInsert:= Menu_GetIndexToInsert(ASubMenu, strItem);
        if NInsert>=0 then
          ASubMenu.Insert(NInsert, mi)
        else
          ASubMenu.Add(mi);
      end
      else
        ASubMenu.Add(mi);

      ASubMenu:= mi;
    end
    else
    begin
      ASubMenu:= ASubMenu.Items[idx];
      bRoot:= false;
    end;
  until false;

  if Assigned(mi) then
  begin
    mi.OnClick:= @MenuPluginClick;
    mi.Tag:= ATag;
  end;
end;

procedure TfmMain.UpdateMenuPlugins;
var
  ListGroups: TStringList;
  ListGroupsVal: TStringList;
  //
  function GroupValue(AName: string): string;
  var
    i: integer;
  begin
    Result:= '';
    AName:= SGetItem(AName, '\');
    for i:= 0 to ListGroups.Count-1 do
    begin
      if SRegexMatchesString(AName, ListGroups[i], false) then
        exit(ListGroupsVal[i]+'\');
    end;
  end;
  //
var
  SCaption, SInMenu: string;
  i: integer;
begin
  if not PythonOK then exit;
  if mnuPlugins=nil then exit;

  mnuPlugins.Clear;
  if Assigned(mnuOpPlugins) then
    mnuOpPlugins.Clear;

  ListGroups:= TStringList.Create;
  ListGroupsVal:= TStringList.Create;
  try
    if AppConfigPluginGroups.Filename<>'' then
    begin
      AppConfigPluginGroups.EnumValues('/', ListGroups);
      for SCaption in ListGroups do
        ListGroupsVal.Add(AppConfigPluginGroups.GetValue('/'+SCaption, ''));
    end;

    for i:= 0 to High(AppPluginsCommand) do
    begin
      if AppPluginsCommand[i].ItemModule='' then Break;
      if AppPluginsCommand[i].ItemFromApi then Continue;

      SCaption:= AppPluginsCommand[i].ItemCaption;
      SInMenu:= AppPluginsCommand[i].ItemInMenu;
      if SInMenu='0' then Continue;

      //add to Plugins
      if (SInMenu='') or (Pos('p', SInMenu)>0) then
        DoOps_AddPluginMenuItem(GroupValue(SCaption)+SCaption, mnuPlugins, i);

      //add to Settings-plugins
      if Assigned(mnuOpPlugins) then
      if Pos('o', SInMenu)>0 then
        DoOps_AddPluginMenuItem(SCaption, mnuOpPlugins, i);
    end;
  finally
    FreeAndNil(ListGroupsVal);
    FreeAndNil(ListGroups);
  end;
end;

procedure TfmMain.UpdateMenuPlugins_Shortcuts(AForceUpdate: boolean = false);
  //
  procedure UpdMenu(AMenu: TMenuItem; AKeymap: TATKeymap);
  var
    miSub: TMenuItem;
    i: integer;
  begin
    for i:= 0 to AMenu.Count-1 do
    begin
      miSub:= AMenu.Items[i];
      if miSub.Count>0 then
        UpdMenu(miSub, AKeymap)
      else
        if miSub.Tag>0 then
          miSub.ShortCut:= AKeymap.GetShortcutFromCommand(cmdFirstPluginCommand+miSub.Tag);
    end;
  end;
  //
var
  NewLexer: string;
  Ed: TATSynEdit;
begin
  if Application.Terminated then exit;
  if not AForceUpdate then
  begin
    NewLexer:= CurrentFrame.LexerName;
    if FLastLexerForPluginsMenu=NewLexer then exit;
    FLastLexerForPluginsMenu:= NewLexer;
  end;

  Ed:= CurrentEditor;
  if Assigned(Ed) then
    UpdMenu(mnuPlugins, Ed.Keymap);
end;


procedure TfmMain.MenuPluginClick(Sender: TObject);
begin
  DoPyCommand_ByPluginIndex((Sender as TComponent).Tag);
end;


