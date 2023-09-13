import traceback

def PrintEx(e):
  tb = traceback.extract_stack()
  name = tb[-2][2]
  print(f'Exception [{name}(...)]: {e}')