import inspect
try:
    import winocr
    print("winocr file:", winocr.__file__)
    print("winocr functions:", dir(winocr))
    print("source of recognize_pil_sync:")
    print(inspect.getsource(winocr.recognize_pil_sync))
except Exception as e:
    print("winocr inspect error:", e)
