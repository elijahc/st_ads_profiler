import numpy as np
import pandas as pd
import streamlit as st
import calmap

# Upload XLS data
with st.sidebar.header('1. Upload your caselog xls  data'):
    uploaded_file = st.sidebar.file_uploader("Upload your input caselog excel file", type=["xls"])
    st.sidebar.markdown("""
[Example XLS input file](https://raw.githubusercontent.com/dataprofessor/data/master/delaney_solubility_with_descriptors.csv)
""")

if uploaded_file is not None:
    @st.cache_data
    def load_xls():
        xls_df = pd.read_excel(uploaded_file,skiprows=10)
        last_row = xls_df.index[xls_df[xls_df.columns[-1]].str.startswith('Case Total')==True].tolist()
        xls_df = xls_df.iloc[:last_row[0]-1].reset_index(drop=True)
        xls_df = xls_df.dropna(axis=1,how='all')
        xls_df = xls_df.rename(columns={k:v for k,v in zip(xls_df.columns,['attr','value','area-val'])})
        # case_idxs = df.attr=='Case Date:'        
        return xls_df 

    df = load_xls()

    def extract_log_meta(df):
        df_dict = df.iloc[:6,:2].to_dict()
        df_dict = {k:v for k,v in zip(df_dict['attr'].values(),df_dict['value'].values())}
        return pd.Series(df_dict)

    def get_log_meta(df):
        return log_meta

    def process_xls(df):
        case_idxs = df.attr=='Case Date:'
        case_grper = case_idxs.astype(int).cumsum()
        log_meta = df.groupby(case_grper).apply(extract_log_meta).reset_index(drop=True)
        log_meta['year'] = log_meta['Case Date:'].dt.year
        log_meta['month'] = log_meta['Case Date:'].dt.month
        log_meta['day_name'] = log_meta['Case Date:'].dt.day_name()

        log_meta_agg = log_meta.groupby(['Case Date:','Case Year:','Site:']).count()['year'].reset_index().rename(columns={'year':'count'})
        log_meta_agg['offset_date'] = log_meta_agg['Case Date:']-pd.Timedelta(546-365, 'd')

        return log_meta, log_meta_agg

    def plot_log(df):
        fig,axs = calmap.calendarplot(
            df.set_index('offset_date')['count'],
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


    lm, lma = process_xls(df)
    # pr = ProfileReport(df, explorative=True)
    st.header('**Case Log yearplot**')
    f,axs = plot_log(lma)
    st.pyplot(f)

    st.write('---')

    st.header('**Input DataFrame**')
    st.write(df)
    
    st.header('**Processed Log**')
    st.write(lma)
