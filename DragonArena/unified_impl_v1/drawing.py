from DragonArenaNew import Knight, Dragon

def ascii_draw(da, me=None):
    w = da._map_width
    h = da._map_height
    print str(da._tick) + '-------------------------------' + da.get_hash()
    for y in range(h):
        ln = ''
        for x in range(w):
            try:
                c = da._loc2creature[(x, y)]
                if c._identifier == me:
                    ln += ' #'
                elif isinstance(c, Dragon):
                    ln += ' O' #+ str(c.get_identifier()[1])
                elif isinstance(c, Knight):
                    ln += ' Y'
            except:
                ln += ' .'
        print(ln)
