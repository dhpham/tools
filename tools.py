#!/Users/pham18/Ureka/variants/common/bin/python

from sys import argv
import re
import pandas as pd
import matplotlib.pyplot as plt
plt.style.use('ggplot')
import datetime as dt
import numpy as np

class FileList():
    def __init__(self, l=[]):
        self.set_list(l)
    
    def set_list(self, l):
        self.__file_list = l
    
    def get_list(self):
        return self.__file_list
    
    def timeline(self, column='date', freq='M', date_label='%m/%Y'):
        print 'Plotting timelines...'
        l = self.get_list()
        for f in l:
            try:
                timeline(f, column, freq, date_label)
            except FileTypeError as e:
                print fte
            except IOError:
                print ' {0}: does not exist'.format(f)
        print 'Done'
    
    def convert(self, type='csv'):
        type = type.lower()
        print 'Converting to .{0}...'.format(type)
        l = self.get_list()
        file_list = []
        for f in l:
            try:
                exec('o=to_{0}(f)'.format(type))
            except FileTypeError as e:
                print fte
                file_list.append(f)
            except IOError:
                print ' {0}: does not exist'.format(f)
            else:
                file_list.append(o)
        print 'Done'
        self.set_list(file_list)

    def export_dates(self, o='dates', type='csv'):
        dates = self.get_dates()
        type = type.lower()
        if type == 'csv':
            dates.to_csv('{0}.{1}'.format(o, type), index=False)
        elif re.search('^xls[xm]?$', type):
            dates.to_excel('{0}.{1}'.format(o, type), index=False)
        return dates
    
    def get_dates(self):
        l = self.get_list()
        mast = {'inst':'instrument', 'id':'obs_id', 'date':'t_min'}
        eso = {'inst':'ins_id', 'id':'dp_id', 'date':'mjd_obs'}
        noao = {'tele':'telescope', 'inst':'instrument', \
            'id':'archive_file', 'date':'date_obs'}
        keck = {'inst':'instrument', 'id':'koaid', 'date':'date_obs', 'time':'ut'}
        sdss = {'id':'objID', 'date':'mjd'}
        dates = pd.DataFrame()
        for f in l:
            path, file_name, ext = file_path(f)
            tgt = file_name.rsplit('.')[0]
            archive = file_name.rsplit('.')[-1].lower()
            df = read(f)
            df['tgt'] = tgt
            tgt = pd.Series(df.tgt, name='target')
            df['arc'] = archive.upper()
            arc = pd.Series(df.arc, name='archive')
            a = eval(archive)
            if archive == 'noao':
                inst = df[a['tele']]+'/'+df[a['inst']]
            elif archive == 'sdss':
                df['instrument'] = 'SDSS'
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
            dates = dates.append(dd).sort_values(by=['target', 'archive', \
                'instrument', 'obs_date'])
        return dates
    
    def plot_tgts(self, logy=False):
        df = self.get_dates()
        tgt = { k for k in df.target.values }
        for t in tgt:
            plot2(df[df.target == t], o=t, title=t, logy=logy)

class FileTypeError(TypeError):
    def __init__(self, f):
        self.f = f
    def __str__(self):
        return ' {0}: invalid file type'.format(self.f)

def mjd_to_dt(mjd, str=False):
    try:
        mjd = float(mjd)
    except ValueError:
        try:
            return dt.datetime.strptime(mjd, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            try:
                return dt.datetime.strptime(mjd, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return mjd
    else: # http://aa.usno.navy.mil/faq/docs/JD_Formula.php
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

def timeline(f, column='date', freq='M', date_label='%m/%Y'):
    path, file_name, ext = file_path(f)
    s = read(f)[column].apply(mjd_to_dt)
    print ' {0} -> {1}{2}.png'.format(f, path, file_name)
    plot(s, path+file_name, title=file_name, freq=freq, date_label=date_label)

def plot2(df, o='plot', title='', freq='M', date_label='%m/%Y', logy=False):
    a = pd.Period(df.obs_date.min(), freq=freq)-1
    b = pd.Period(df.obs_date.max(), freq=freq)+1
    r = pd.period_range(start=a, end=b, freq=freq)
    inst = { k for k in df.instrument.values }
    t = pd.DataFrame(data=0, columns=inst, index=r)
    for i in inst:
        s = pd.PeriodIndex(df[df.instrument == i].obs_date.values, freq=freq)
        cnt = s.value_counts()
        t[i] = t[i].add(cnt, fill_value=0)
    fig, ax = plt.subplots()
    ax.set_axis_bgcolor((1,1,1))
    ax.grid(color=(0.9,0.9,0.9))
    p = t.plot(kind='bar', figsize=(25,15), ax=ax, fontsize=9, logy=logy)
    p.set_title(title)
    p.set_xlabel('Date')
    p.set_ylabel('Count')
    p.set_xticklabels([ k.strftime(date_label) for k in t.index ])
    fig.savefig('{0}.png'.format(o), dpi=600)

def plot(s, o='plot', title='', freq='M', date_label='%m/%Y'):
    s = pd.PeriodIndex(s.values, freq=freq)
    a = s.min()-1
    b = s.max()+1
    r = pd.period_range(start=a, end=b, freq=freq)
    bins = pd.Series([0]*len(r), index=r)
    cnts = s.value_counts()
    t = bins.add(cnts, fill_value=0)
    
    fig, ax = plt.subplots()
    p = t.plot(kind='bar', figsize=(20,15), ax=ax)
    p.set_title(title)
    p.set_xlabel('Date')
    p.set_ylabel('Count')
    p.set_xticklabels([ k.strftime(date_label) for k in t.index ])
    fig.savefig('{0}.png'.format(o), dpi=600)

def read(f, s='Sheet1'):
    path, file_name, ext = file_path(f)
    if ext == 'csv':
        df = pd.read_csv(f, comment='#')
    elif re.search('^xls[xm]?$', ext):
        df = pd.read_excel(f, sheetname=s)
    elif ext == 'tbl':
        df = pd.read_fwf(f, comment='\\', skiprows=[6,7,8])
        df.columns = [ k[:-1] for k in df.columns.values ]
    elif ext == 'vot' or ext == 'xml':
        df = read_vot(f)
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

def to_csv(f):
    df = read(f)
    path, file_name, ext = file_path(f)
    print ' {0} -> {1}{2}.csv'.format(f, path, file_name)
    df.to_csv(path+file_name+'.csv', sep=',', index=False)
    return '{0}{1}.csv'.format(path, file_name)

def to_xls(f):
    df = read(f)
    path, file_name, ext = file_path(f)
    print ' {0} -> {1}{2}.xls'.format(f, path, file_name)
    df.to_excel(path+file_name+'.xls', sheet_name='Sheet1', index=False)
    return '{0}{1}.xls'.format(path, file_name)

def to_xlsx(f):
    df = read(f)
    path, file_name, ext = file_path(f)
    print ' {0} -> {1}{2}.xlsx'.format(f, path, file_name)
    df.to_excel(path+file_name+'.xlsx', sheet_name='Sheet1', index=False)
    return '{0}{1}.xlsx'.format(path, file_name)

def file_path(f):
    path = f.rsplit('/', 1)[0]+'/' if '/' in f else ''
    file_name = f.rsplit('/', 1)[-1].rsplit('.', 1)[0]
    ext = f.rsplit('.', 1)[-1].lower()
    return path, file_name, ext

# http://www.bdnyc.org/2012/10/decimal-deg-to-hms/
def hms_to_deg(ra='', dec=''):
    if ra:
        H,M,S = [ abs(float(k)) for k in ra.split(':') ]
        ra = H*15 + M/4 + S/240
    if dec:
        s = -1 if dec[0] == '-' else 1
        D,M,S = [ abs(float(k)) for k in dec.split(':') ]
        dec = s * ( D + M/60 + S/3600 )
    if ra and dec:
        return ra, dec
    else:
        return ra or dec

if __name__ == '__main__':
    fl = FileList(argv[1:])
    df = fl.export_dates(o='brown_dwarf')
    fl.plot_tgts(logy=True)