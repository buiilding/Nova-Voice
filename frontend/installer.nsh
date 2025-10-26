!macro customUnInstall
  # Remove user data directory on uninstall
  RMDir /r "$PROFILE\.nova-voice"
!macroend
