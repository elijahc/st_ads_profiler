import numpy as np
import pandas as pd
import streamlit as st
import calmap

# Upload XLS data
with st.sidebar.header('1. Upload your caselog'):
    uploaded_file = st.sidebar.file_uploader("Upload ADS case log (xls)", type=["xls"])
    st.sidebar.markdown("""
        [Example XLS input file](https://github.com/elijahc/st_ads_profiler/raw/master/ref/ACLResProcDetail-edc-sample.xls)
        """)

    st.sidebar.markdown("""
        [How to download caselog from ACGME](https://www.loom.com/share/9bc9d25c013b489abec09eb086bff1c9?sid=27f43eeb-4f16-4565-9cd4-c16a548ad252)
    """) 

if uploaded_file is not None:
    def load_xls():
        xls_df = pd.read_excel(uploaded_file,skiprows=10)
        df_end = xls_df[-10:]
        last_row = df_end.index[df_end[df_end.columns[-1]].str.startswith('Case Total')==True].tolist()[0]
        last_row = last_row-1
        xls_df = xls_df.iloc[:last_row]
        xls_df = xls_df.dropna(axis=1,how='all').dropna(axis=0,how='all')
        xls_df = xls_df.rename(columns={k:v for k,v in zip(xls_df.columns,['attr','value','area-val'])}).reset_index(drop=True)
        # case_idxs = df.attr=='Case Date:'        
        return xls_df
    
    df = load_xls()

    def extract_log_meta(df):
        df_dict = df.iloc[:6,:2].to_dict()
        df_dict = pd.Series({k:v for k,v in zip(df_dict['attr'].values(),df_dict['value'].values())})
        return df_dict

    @st.cache_data
    def process_xls(df):
        case_idxs = df.attr=='Case Date:'
        case_grper = case_idxs.astype(int).cumsum()
        log_meta = df.groupby(case_grper).apply(extract_log_meta).reset_index(drop=True)
        log_meta['year'] = log_meta['Case Date:'].dt.year
        log_meta['month'] = log_meta['Case Date:'].dt.month
        log_meta['day_name'] = log_meta['Case Date:'].dt.day_name()

        return log_meta
    
    lm = process_xls(df)

    def plot_log(log_meta):
        log_meta_agg = log_meta.groupby(['Case Date:','Case Year:','Site:']).count()['year'].reset_index().rename(columns={'year':'count'})
        log_meta_agg['offset_date'] = log_meta_agg['Case Date:']-pd.Timedelta(546-365, 'd')

        fig,axs = calmap.calendarplot(
            log_meta_agg.set_index('offset_date')['count'],
            cmap='YlGn',
            fillcolor='lightgrey',
            linewidth=2,
            fig_kws={'figsize':(8,8)},
            daylabels=list('MTWTFSS'),
            dayticks=[0, 2, 4, 6],
            monthly_border=True,
        );
        for ax in axs:
            ax.set_xticklabels(['Jul','Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr','May','Jun']);
        
        return fig,axs

    st.header('**Case Log yearplot**')
    f,axs = plot_log(lm)
    st.pyplot(f)

    st.write('---')

    st.header('**Input DataFrame**')
    st.write(df)

    st.write('---')

    st.header('**Processed Log**')
    st.write(lm)
