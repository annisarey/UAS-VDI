"""Pra-pemrosesan: gabung CSV BPS + batas wilayah, sederhanakan geometri, hasilkan JSON ringan."""
import json,csv,re,sys
SRC=sys.argv[1] if len(sys.argv)>1 else '../raw'
num=lambda s:(None if s.strip() in('','-') else float(s.replace(',','.')))
def rd(f):return list(csv.DictReader(open(f'{SRC}/{f}',encoding='utf-8-sig'),delimiter=';'))
def norm(s):return re.sub(r'[^A-Z]','',re.sub(r'^(KOTA|KAB\.?|KABUPATEN)\s+','',s.upper().strip()))
# ---- geospasial
def dp(p,t):
    if len(p)<4:return p
    (x1,y1),(x2,y2)=p[0],p[-1];dx,dy=x2-x1,y2-y1;L=(dx*dx+dy*dy)**.5 or 1e-12
    m,i=0,0
    for k in range(1,len(p)-1):
        d=abs(dy*(p[k][0]-x1)-dx*(p[k][1]-y1))/L
        if d>m:m,i=d,k
    return dp(p[:i+1],t)[:-1]+dp(p[i:],t) if m>t else [p[0],p[-1]]
def ring(r,t=0.012):
    r=[(x,y) for x,y in r];h=len(r)//2   # cincin tertutup: pecah dua agar Douglas-Peucker valid
    r=dp(r[:h+1],t)[:-1]+dp(r[h:],t)
    r=[[round(x,2),round(y,2)] for x,y in r]
    return r if len(r)>=4 else None
def area(r):return abs(sum(r[i][0]*r[i+1][1]-r[i+1][0]*r[i][1] for i in range(len(r)-1)))/2
g=json.load(open(f'{SRC}/administrasi_kabkota.geojson'))
rows=rd('geospasial.csv');tab={}
for r in rows:
    nm=r['kabkota'];AL={'Kota Baru':'KOTABARU','Mahakam Ulu':'MAHAKAMHULU','Mamuju Utara':'PASANGKAYU'}
    k=(nm.upper().startswith('KOTA '),AL.get(nm) or norm(nm))
    if nm in AL:k=(False,AL[nm])
    tab[k]=dict(ikk=num(r['ikk']),pdrb=num(r['pdrb']),pdrb_f=num(r['pdrb_f']),nama=r['kabkota'])
feats=[];used=set();miss=[]
for f in g['features']:
    p=f['properties'];kota=int(p['kdkab'])>=71
    n=re.sub(r'[^A-Z]','',p['nmkab'])
    alias={'SIAK':'SIAK','KOTABARU':'KOTABARU'}
    k=(kota,n)
    if k not in tab:k=(kota,n.replace('SIAK','SIAK'))
    if k not in tab:miss.append((kota,p['nmkab']));continue
    used.add(k);v=tab[k]
    polys=f['geometry']['coordinates'] if f['geometry']['type']=='MultiPolygon' else [f['geometry']['coordinates']]
    out=[]
    for po in polys:
        rs=[ring(r) for r in po];rs=[r for r in rs if r and area(r)>0.0004]
        if rs and area(rs[0])>0.0004:out.append(rs)
    if not out:continue
    feats.append(dict(type='Feature',properties=dict(id=p['kdprov']+p['kdkab'],nama=v['nama'],prov=p['nmprov'].title(),ikk=v['ikk'],pdrb=v['pdrb'],pdrb_f=v['pdrb_f'],
      share=(round(100*v['pdrb_f']/v['pdrb'],2) if v['pdrb_f'] and v['pdrb'] else None)),geometry=dict(type='MultiPolygon',coordinates=out)))
print('geo cocok',len(feats),'tak cocok',len(miss),miss[:30]);print('csv tak terpakai',[tab[k]['nama'] for k in tab if k not in used])
json.dump(dict(type='FeatureCollection',features=feats),open('data/kabkota.geojson','w'),separators=(',',':'))
# ---- hierarki
pulau={'ACEH':'Sumatera','SUMATERA UTARA':'Sumatera','SUMATERA BARAT':'Sumatera','RIAU':'Sumatera','JAMBI':'Sumatera','SUMATERA SELATAN':'Sumatera','BENGKULU':'Sumatera','LAMPUNG':'Sumatera','KEP. BANGKA BELITUNG':'Sumatera','KEP. RIAU':'Sumatera',
'DKI JAKARTA':'Jawa','JAWA BARAT':'Jawa','JAWA TENGAH':'Jawa','DI YOGYAKARTA':'Jawa','JAWA TIMUR':'Jawa','BANTEN':'Jawa','BALI':'Bali & Nusa Tenggara','NUSA TENGGARA BARAT':'Bali & Nusa Tenggara','NUSA TENGGARA TIMUR':'Bali & Nusa Tenggara',
'KALIMANTAN BARAT':'Kalimantan','KALIMANTAN TENGAH':'Kalimantan','KALIMANTAN SELATAN':'Kalimantan','KALIMANTAN TIMUR':'Kalimantan','KALIMANTAN UTARA':'Kalimantan',
'SULAWESI UTARA':'Sulawesi','SULAWESI TENGAH':'Sulawesi','SULAWESI SELATAN':'Sulawesi','SULAWESI TENGGARA':'Sulawesi','GORONTALO':'Sulawesi','SULAWESI BARAT':'Sulawesi','MALUKU':'Maluku & Papua','MALUKU UTARA':'Maluku & Papua','PAPUA BARAT':'Maluku & Papua','PAPUA':'Maluku & Papua','PAPUA BARAT DAYA':'Maluku & Papua'}
H=[];bad=[]
for r in rd('hierarchy.csv'):
    p=r['provinsi'].strip().upper()
    if p in('INDONESIA','','CATATAN') or r['kons_gedung'].strip() in('-',''):continue
    if p not in pulau:bad.append(p);continue
    H.append(dict(pulau=pulau[p],provinsi=p.title().replace('Di ','DI ').replace('Dki','DKI').replace('Kep.','Kep.'),Gedung=num(r['kons_gedung']),Sipil=num(r['kons_sipil']),Khusus=num(r['kons_khusus'])))
print('hierarki',len(H),'tak terpetakan',bad)
json.dump(H,open('data/hierarki.json','w'),ensure_ascii=False)
# ---- multivariat
V=[('ikk','IKK'),('pdrb_f','PDRB Konstruksi'),('jmlh_perusahaan','Jml Perusahaan'),('indeks_konstruksiselesai','Idx Nilai Selesai'),('balasjasa_upah','Idx Balas Jasa'),('indeks_pekerjatetap','Idx Pekerja Tetap'),('hari_pekerjaharian','Idx Hari Harian'),('belanja_modal','Belanja Modal')]
M=[];drop=[]
for r in rd('multivariate.csv'):
    p=r['provinsi'].strip().upper()
    if p=='INDONESIA':continue
    vals=[num(r[k]) for k,_ in V]
    if None in vals:drop.append(p);continue
    M.append(dict(provinsi=p.title().replace('Di ','DI ').replace('Dki','DKI'),pulau=pulau.get(p,'?'),v=vals))
print('multivariat',len(M),'dibuang (NA)',drop)
json.dump(dict(vars=[n for _,n in V],rows=M,dropped=drop),open('data/multivariat.json','w'),ensure_ascii=False)
