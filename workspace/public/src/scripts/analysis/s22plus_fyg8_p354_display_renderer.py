"""P353 static image and 30HS, with explicit CRTC noise disable in one commit."""
from pathlib import Path
import hashlib
import s22plus_fyg8_p353_display_renderer as predecessor

PREDECESSOR_SHA = '3334bb86decd69791a17d87d038c7dda48a8f5df609b2cf7afc5a07b638bcbc7'


def render():
    if hashlib.sha256(Path(predecessor.__file__).read_bytes()).hexdigest() != PREDECESSOR_SHA:
        raise ValueError('P354 renderer predecessor changed')
    source = predecessor.render().decode()
    changes = (
        ('ids[13+2*LIMIT]', 'ids[14+2*LIMIT]'),
        ('values[13+2*LIMIT]', 'values[14+2*LIMIT]'),
        ('objects[0]=s.crtc;counts[0]=2;', 'objects[0]=s.crtc;counts[0]=3;'),
        ('    objects[1]=s.connector;',
         '    /* Volatile property: submit zero even when its cached value is zero. */\n'
         '    ids[2]=property(&rp,"noise_layer_v1",NULL);values[2]=0;\n'
         '    objects[1]=s.connector;'),
        ('ids[2]=property(&cp,"CRTC_ID",NULL);values[2]=s.crtc;',
         'ids[3]=property(&cp,"CRTC_ID",NULL);values[3]=s.crtc;'),
        ('ids[3+i]=property(&pp,names[i],NULL);values[3+i]=selected[i];',
         'ids[4+i]=property(&pp,names[i],NULL);values[4+i]=selected[i];'),
        ('ids[14+2*i]=property(&p,"CRTC_ID",NULL);values[14+2*i]=0;',
         'ids[15+2*i]=property(&p,"CRTC_ID",NULL);values[15+2*i]=0;'),
        ('ids[13+2*i]=property(&p,"FB_ID",NULL);values[13+2*i]=0;',
         'ids[14+2*i]=property(&p,"FB_ID",NULL);values[14+2*i]=0;'),
    )
    for old, new in changes:
        if source.count(old) != 1:
            raise ValueError('P354 renderer seam differs: ' + old)
        source = source.replace(old, new, 1)
    return source.encode()
