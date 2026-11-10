"""Render editable conceptual request and credential-lifecycle workflow assets."""
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets"
BG, PANEL, BORDER, TEXT, MUTED = "#0b1220", "#142135", "#34465f", "#f1f5f9", "#b3c3d8"
GREEN, CYAN, PURPLE, AMBER = "#b4ef65", "#65d7ee", "#b8a0ff", "#ffc478"


def font(size, bold=False):
    return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)

F = {n: font(n) for n in (18, 20, 22, 24)}
F[44], F[26] = font(44, True), font(26, True)


def render(stage=None, progress=0):
    im = Image.new("RGB", (1560, 900), BG)
    d = ImageDraw.Draw(im)
    d.text((50, 40), "One entry point. Explicit access. Controlled keys.", font=F[44], fill=TEXT)
    d.text((52, 110), "BLASTER  /  NGINX + Apache APISIX  /  RAG, inference, and agent APIs", font=F[24], fill=MUTED)
    def line(points, color, active):
        d.line(points, fill=color, width=3, joint="curve")
        x,y=points[-1];px,py=points[-2];a=math.atan2(y-py,x-px)
        d.polygon([(x,y)]+[(x-14*math.cos(a+t),y-14*math.sin(a+t)) for t in (-0.48,0.48)],fill=color)
        if stage == active:
            lengths=[math.dist(a,b) for a,b in zip(points,points[1:])];dist=progress*sum(lengths)
            for (a,b),length in zip(zip(points,points[1:]),lengths):
                if dist<=length:
                    t=dist/length if length else 0;x=a[0]+t*(b[0]-a[0]);y=a[1]+t*(b[1]-a[1])
                    d.ellipse((x-7,y-7,x+7,y+7),fill=TEXT);break
                dist-=length
    def card(x,y,w,h,title,lines,active,color):
        lit=stage is None or stage==active
        d.rounded_rectangle((x,y,x+w,y+h),radius=16,fill=PANEL,outline=color if lit else BORDER,width=3 if lit else 2)
        d.rounded_rectangle((x+18,y+20,x+23,y+h-20),radius=2,fill=color if lit else BORDER)
        d.text((x+37,y+20),title,font=F[26],fill=TEXT)
        for i,t in enumerate(lines):d.text((x+37,y+65+i*30),t,font=F[20],fill=MUTED)
    d.text((52,178),"DATA PLANE  /  REQUEST PATH",font=F[18],fill=CYAN)
    line([(305,300),(400,300)],CYAN,0)
    line([(710,300),(805,300)],GREEN,1)
    line([(1145,300),(1220,300)],PURPLE,2)
    line([(950,540),(950,400)],AMBER,3)
    line([(710,625),(805,625)],AMBER,3)
    card(50,220,255,180,"Client",["Trusted HTTPS","apikey header","Host: 192.168.15.10"],0,CYAN)
    card(400,220,310,180,"NGINX edge",["TLS termination","No direct bypass","Legacy paths included"],0,CYAN)
    card(805,220,340,180,"APISIX policy",["Authenticate consumer","Check service allowlist","Rewrite + hide credentials"],1,GREEN)
    card(1220,220,290,180,"AI backends",["RAG / invoke","Inference / v1","Agent / ask"],2,PURPLE)
    d.text((52,495),"CONFIGURATION PLANE  /  NOT A PER-REQUEST VAULT LOOKUP",font=F[18],fill=AMBER)
    card(400,540,310,180,"Vault KV v2",["Externally held keys","Scoped reader only","Manual unseal lifecycle"],3,AMBER)
    card(805,540,340,180,"Renderer",["Public routes + private keys","Validate, write, replace","Ignored private runtime file"],3,AMBER)
    d.text((52,590),"LAN example",font=F[22],fill=TEXT)
    d.text((52,630),"Router: 192.168.15.1",font=F[20],fill=MUTED)
    captions=[("01  ENTER OVER HTTPS","Certificate trust stays enabled; TLS material is supplied outside the repository."),
              ("02  CHECK IDENTITY AND SCOPE","Missing or invalid key: 401. Authenticated but outside the service allowlist: 403."),
              ("03  CALL THE SELECTED BACKEND","All service aliases use the same policy boundary; client keys are hidden upstream."),
              ("04  UPDATE THE KEY LIFECYCLE","Render from the secret store, apply atomically, then verify rotation or revocation.")]
    label,detail=captions[stage] if stage is not None else ("TWO PLANES, ONE REVIEWABLE SYSTEM","Request routing and credential updates are separate; Vault is not queried for every inference.")
    d.text((52,770),label,font=F[22],fill=GREEN)
    d.text((52,812),detail,font=F[20],fill=TEXT)
    d.text((52,868),"Conceptual animation. Fictional addresses. Timing does not represent measured performance.",font=F[18],fill=MUTED)
    return im


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    render().save(OUT/"blaster-workflow.png",optimize=True)
    palette=render().quantize(colors=128)
    frames=[render(stage,step/11).quantize(palette=palette,dither=Image.Dither.NONE) for stage in range(4) for step in range(12)]
    frames[0].save(OUT/"blaster-workflow.gif",save_all=True,append_images=frames[1:],duration=150,loop=0,optimize=True,disposal=2)
    print("Generated static PNG and 48-frame workflow animation")


if __name__ == "__main__":main()
