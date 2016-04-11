#!/Users/pham18/Ureka/variants/common/bin/python

from sys import argv
import re
import pandas as pd
import matplotlib.pyplot as plt
plt.style.use('ggplot')
import datetime as dt
import subprocess

class FileList():
    def __init__(self, l=[]):
        self.set_list(l)
        self.__dates = None
    
    def set_list(self, l):
        self.__file_list = l
    
    def get_list(self):
        return self.__file_list

class SearchResults():
    def __init__(self, l=[]):
        self.set_list(l)
        self.__dates = None
    
    def set_list(self, l):
        self.__file_list = l
    
    def get_list(self):
        return self.__file_list
    
    def timeline(self, column='date', freq='M', date_label='%m/%Y'):
        print 'Making timelines...'
        l = self.get_list()
        for f in l:
            try:
                timeline(f, column, freq, date_label)
            except FileTypeError as e:
                print fte
            except IOError:
                print ' {0}: does not exist'.format(f)
        print 'Done'
    
    def convert(self, type='csv', update=True, p=''):
        type = type.lower()
        subprocess.call(['mkdir', p])
        print 'Converting to .{0}...'.format(type)
        l = self.get_list()
        file_list = []
        i = 0
        n = len(l)
        for f in l:
            i += 1
            path, file_name, ext = file_path(f)
            print ' [{0}/{1}] {2} -> {3}{4}.{5}'.format(i, n, f, p, file_name, type)
            try:
                exec('o=to_{0}(f, p=p)'.format(type))
            except FileTypeError as e:
                print e
                file_list.append(f)
            except IOError:
                print ' {0}: does not exist'.format(f)
            else:
                file_list.append(o)
        print 'Done'
        self.set_list(file_list) if update else None

    def export_dates(self, o='dates', type='csv'):
        dates = self.get_dates() if self.__dates is None else self.__dates
        print 'Exporting dates to {0}.{1}...'.format(o, type)
        type = type.lower()
        if type == 'csv':
            dates.to_csv('{0}.{1}'.format(o, type), index=False)
        elif re.search('^xls[xm]?$', type):
            dates.to_excel('{0}.{1}'.format(o, type), index=False)
        print 'Done'
        return dates
    
    def get_dates(self):
        print 'Reading files...'.format()
        l = self.get_list()
        mast = {'inst':'instrument', 'id':'obs_id', 'date':'t_min'}
        #eso = {'inst':'ins_id', 'id':'dp_id', 'date':'mjd_obs'}
        eso = {'inst':'Instrument', 'id':'Dataset ID', 'date':'MJD-OBS'}
        noao = {'tele':'telescope', 'inst':'instrument', \
            'id':'archive_file', 'date':'date_obs'}
        keck = {'inst':'instrument', 'id':'koaid', 'date':'date_obs', 'time':'ut'}
        sdss = {'id':'objID', 'date':'mjd'}
        dates = pd.DataFrame()
        i = 0
        max = len(l)
        for f in l:
            path, file_name, ext = file_path(f)
            i += 1
            print ' [{0}/{1}] {2}{3}.{4}'.format(i, max, path, file_name, ext)
            tgt = file_name.rsplit('.')[0]
            archive = file_name.rsplit('.')[1].lower()
            df = read(f)
            df['tgt'] = tgt
            tgt = pd.Series(df.tgt, name='target_name')
            df['arc'] = archive.upper()
            arc = pd.Series(df.arc, name='archive')
            a = eval(archive)
            if archive == 'noao':
                inst = df[a['tele']]+'/'+df[a['inst']]
            elif archive == 'sdss':
                df['instrument'] = 'SDSS'
                inst = df['instrument']
            elif archive == 'keck':
                inst = df['instrument']
            else:
                inst = df[a['inst']]
            inst = pd.Series(inst, name='instrument')
            id = df[a['id']]
            id = pd.Series(id, name='obs_id')
            date = df[a['date']]+' '+df[a['time']] if archive == 'keck' else \
                df[a['date']]
            date = pd.Series(date, name='obs_date')
            date = date.apply(mjd_to_dt)
            dd = pd.concat([tgt, arc, inst, id, date], axis=1)
            dates = dates.append(dd).sort_values(by=['target_name', 'archive', \
                'instrument', 'obs_date'])
        print 'Done'
        self.__dates = dates
        return dates
    
    def plot_tgts(self, logy=False, p=''):
        dates = self.get_dates() if self.__dates is None else self.__dates
        subprocess.call(['mkdir', p])
        print 'Making timelines...'
        targets = { k for k in dates.target_name.values }
        i = 0
        n = len(targets)
        for tgt in targets:
            i += 1
            print ' [{0}/{1}] {2}'.format(i, n, title)
            plot2(dates[dates.target_name == tgt], o=tgt, title=tgt, logy=logy, p=p)
        print 'Done'
    
    def export_totals(self, o='totals'):
        print 'Writing file...'
        dates = self.get_dates() if self.__dates is None else self.__dates
        d = dates.copy()
        d['n'] = int(1)
        t = pd.pivot_table(d, values='n', index='target_name', columns=['archive'], \
            aggfunc=sum, fill_value=0)
        t['total'] = t.sum(axis=1)
        print ' {0}.txt'.format(o)
        t.to_csv('{0}.txt'.format(o), sep='\t')
        print 'Done'
        return t

class FileTypeError(TypeError):
    def __init__(self, f):
        self.f = f
    def __str__(self):
        return ' {0}: invalid file type'.format(self.f)

def mjd_to_dt(mjd, str=False):
    try: # http://aa.usno.navy.mil/faq/docs/JD_Formula.php
        mjd = float(mjd)
        jd = mjd + 2400000.5
        jd = jd + .5
        z = int(jd)
        f = jd % 1
        if z < 2299161:
            a = z
        else:
            alpha = int((z-1867216.25)/36524.25)
            a = z + 1 + alpha - int(alpha/4)
        b = a + 1524
        c = int((b-122.1)/365.25)
        d = int(365.25*c)
        e = int((b-d)/30.6001)
        dd = b - d - int(30.6001*e) + f
        mm = e - 1 if e < 13.5 else e - 13
        yyyy = c - 4716 if mm > 2.5 else c - 4715
        h = (dd%1)*24
        m = (h%1)*60
        s = (m%1)*60
        us = (s%1)*10**6
        return dt.datetime(yyyy, mm, int(dd), int(h), int(m), int(s), int(us))
    except ValueError:
        try:
            return dt.datetime.strptime(mjd, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            try:
                return dt.datetime.strptime(mjd, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                print ValueError
                return mjd
        except TypeError:
            print TypeError
            return mjd

def timeline(f, column='date', freq='M', date_label='%m/%Y'):
    path, file_name, ext = file_path(f)
    s = read(f)[column].apply(mjd_to_dt)
    print ' {0} -> {1}{2}.png'.format(f, path, file_name)
    plot(s, path+file_name, title=file_name, freq=freq, date_label=date_label)

def plot2(df, o='plot', p='', title='', freq='M', date_label='%m/%Y', logy=False):
    a = pd.Period(df.obs_date.min(), freq=freq)-1
    b = pd.Period(df.obs_date.max(), freq=freq)+1
    r = pd.period_range(start=a, end=b, freq=freq)
    inst = { k for k in df.instrument.values }
    t = pd.DataFrame(data=0, columns=inst, index=r)
    for i in inst:
        s = pd.PeriodIndex(df[df.instrument == i].obs_date.values, freq=freq)
        cnt = s.value_counts()
        t[i] = t[i].add(cnt, fill_value=0).astype(int)
    fig, ax = plt.subplots()
    ax.set_axis_bgcolor((1,1,1))
    ax.grid(color=(0.9,0.9,0.9))
    w = len(r)/3
    pl = t.plot(kind='bar', figsize=(w,11), ax=ax, logy=logy)
    pl.set_title(title)
    pl.set_xlabel('Date')
    pl.set_ylabel('Count')
    pl.set_xticklabels([ k.strftime(date_label) for k in t.index ])
    fig.savefig('{0}{1}.png'.format(p, o), dpi=300)
    plt.close(fig)

def plot(s, o='plot', p='', title='', freq='M', date_label='%m/%Y'):
    s = pd.PeriodIndex(s.values, freq=freq)
    a = s.min()-1
    b = s.max()+1
    r = pd.period_range(start=a, end=b, freq=freq)
    bins = pd.Series([0]*len(r), index=r)
    cnts = s.value_counts()
    t = bins.add(cnts, fill_value=0)
    
    fig, ax = plt.subplots()
    pl = t.plot(kind='bar', figsize=(20,15), ax=ax)
    pl.set_title(title)
    pl.set_xlabel('Date')
    pl.set_ylabel('Count')
    pl.set_xticklabels([ k.strftime(date_label) for k in t.index ])
    fig.savefig('{0}{1}.png'.format(p, o), dpi=300)
    plt.close(fig)

def read(f, s='Sheet1'):
    path, file_name, ext = file_path(f)
    if ext == 'csv':
        df = pd.read_csv(f, sep=',', skipinitialspace=True)
    elif re.search('^xls[xm]?$', ext):
        df = pd.read_excel(f, sheetname=s)
    elif ext == 'tbl':
        df = pd.read_fwf(f, comment='\\', skiprows=[6,7,8])
        df.columns = [ k[:-1] for k in df.columns.values ]
    elif ext == 'vot' or ext == 'xml':
        df = read_vot(f)
    elif ext == 'txt':
        df = pd.read_csv(f, skipinitialspace=True)
    else:
        raise FileTypeError(f)
    return df

def read_vot(f):
    with open(f, 'r') as vot_file:
        vot = vot_file.read().replace('\n', ' ')
    field_names = re.findall('<FIELD.*?>', vot, re.I|re.S)
    field_names = [ re.search('name=["\'].*?["\']', k, re.I|re.S).group()[6:-1] \
        for k in field_names ]
    TR = re.findall('<TR>.*?</TR>', vot, re.I|re.S)
    TD = [ re.findall('<TD>.*?</TD>', k, re.I|re.S) for k in TR ]
    t = [ [ j[4:-5] for j in k ] for k in TD ]
    df = pd.DataFrame(t, columns=field_names)
    return df

def to_csv(f, p=''):
    df = read(f)
    path, file_name, ext = file_path(f)
    df.to_csv(p+file_name+'.csv', sep=',', index=False)
    return '{0}{1}.csv'.format(p, file_name)

def to_xls(f, p=''):
    df = read(f)
    path, file_name, ext = file_path(f)
    df.to_excel(p+file_name+'.xls', sheet_name='Sheet1', index=False)
    return '{0}{1}.xls'.format(p, file_name)

def to_xlsx(f, p=''):
    df = read(f)
    path, file_name, ext = file_path(f)
    df.to_excel(p+file_name+'.xlsx', sheet_name='Sheet1', index=False)
    return '{0}{1}.xlsx'.format(p, file_name)

def file_path(f):
    path = f.rsplit('/', 1)[0]+'/' if '/' in f else ''
    file_name = f.rsplit('/', 1)[-1].rsplit('.', 1)[0]
    ext = f.rsplit('.', 1)[-1].lower()
    return path, file_name, ext

# http://www.bdnyc.org/2012/10/decimal-deg-to-hms/
def hms_to_deg(ra=None, dec=None):
    if ra and type(ra) is str :
        sep = ':' if (':' in ra) else ' '
        H,M,S = [ abs(float(k)) for k in ra.split(sep) ]
        ra = H*15 + M/4 + S/240
    if dec and type(dec) is str:
        s = -1 if dec[0] == '-' else 1
        sep = ':' if (':' in dec) else ' '
        D,M,S = [ abs(float(k)) for k in dec.split(sep) ]
        dec = s * ( D + M/60 + S/3600 )
    if ra and dec:
        return ra, dec
    else:
        return ra or dec

def queries(f, o1='sdss_queries', o2='noao_queries'):
    df = read(f)
    with open('{0}.txt'.format(o1), 'w') as f:
        for k in df.iterrows():
            row = k[1]
            name = row[0]
            ra = row['ra']
            dec = row['dec']
            ra, dec = hms_to_deg(ra, dec)
            f.write('-- '+name+'\n')
            f.write('SELECT *\n')
            f.write('FROM fGetNearbyObjEq({0},{1},3) n, PhotoPrimary p\n'.format(ra, dec))
            f.write('WHERE n.objID=p.objID\n\n')
    with open('{0}.txt'.format(o2), 'w') as f:
        for k in df.iterrows():
            row = k[1]
            name = row[0]
            ra = row['ra']
            dec = row['dec']
            ra, dec = hms_to_deg(ra, dec)
            ram = str(float(ra)-1./6)
            rap = str(float(ra)+1./6)
            decm = str(float(dec)-1./6)
            decp = str(float(dec)+1./6)
            f.write('-- '+name+'\n')
            f.write('SELECT reference, dtpropid, surveyid, release_date, start_date, date_obs, dtpi, ra, dec, telescope, instrument, filter, exposure, obstype, obsmode, proctype, prodtype, seeing, depth, dtacqnam, reference AS archive_file, filesize, md5sum\n')
            f.write('FROM voi.siap\n')
            f.write('WHERE ((dec >= {0} AND dec <= {1}) AND (ra >= {2} AND ra <= {3})) AND (proctype = \'Raw\') AND NOT ((telescope = \'kpcf\' AND instrument = \'ccd_spec\') OR (telescope = \'kp21m\' AND instrument = \'ccd_spec\') OR (telescope = \'kp4m\' AND instrument = \'kosmos\') OR (telescope = \'wiyn\' AND instrument = \'bench\') OR (telescope = \'ct15m\' AND instrument = \'ccd_spec\') OR (telescope = \'ct15m\' AND instrument = \'echelle\') OR (telescope = \'ct4m\' AND instrument = \'ccd_spec\') OR (telescope = \'ct4m\' AND instrument = \'cosmos\') OR (telescope = \'ct4m\' AND instrument = \'triplespec4\') OR (telescope = \'soar\' AND instrument = \'goodman\'))\n'.format(decm, decp, ram, rap))
            f.write('ORDER BY date_obs ASC LIMIT 50000\n\n')

def remove_comments(file, comment='#'):
    with open(file, 'r') as f:
        lines = f.readlines()
    with open(file, 'w') as f:
        for l in lines:
            if (l[0] != '#'):
                f.write(l)

if __name__ == '__main__':
    coords = argv[1]
    list = argv[2:]
    queries(coords)
    
    #df = read(coords)
    #df['ra'] = df['ra'].apply(lambda x: hms_to_deg(x, None))
    #df['dec'] = df['dec'].apply(lambda x: hms_to_deg(None, x))
    #print df
    
    fl = SearchResults(list)
    fl.convert('xlsx', p='search_results/')
    fl.get_dates()
    fl.export_totals()
    fl.export_dates(o='brown_dwarf_dates')
    fl.plot_tgts(logy=True, p='plots/')