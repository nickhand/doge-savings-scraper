import pandas as pd
import os

def diff_scrapes(new_path, old_path):
    '''Print difference between two scrape files (by file path)
    Prints rows added, rows deleted, rows modified 
    Rows modified is split in 2 sections: 
        Rows with changes outside of modNumber - These may be more substantive
        Rows with changes to modNumber only - These are more common and on a lag in FPDS (e.g. we except to see termination for convenience recorded on every contract at some point)'''

    new_df = load_scrape(new_path)
    new_df['version'] = 'new'
    old_df = load_scrape(old_path)
    old_df['version'] = 'old'

    print('****************')
    print('Scrape Diff:')
    print('new =',new_path)
    print('old =',old_path)
    print()

    add_df = new_df[~new_df.PIID.isin(old_df.PIID)]
    print("**Rows Added:",len(add_df))
    if(len(add_df)>0):
        print(add_df[['PIID','modNumber','business_name','claimed_savings','total_contract','description']])
    print()

    del_df = old_df[~old_df.PIID.isin(new_df.PIID)]
    print("**Rows Removed:",len(del_df))
    if(len(del_df)>0):
        print(del_df[['PIID','modNumber','business_name','claimed_savings','total_contract','description']])
    print()

    changes_df = pd.concat([new_df,old_df])
    changes_df = changes_df[~changes_df.PIID.isin(pd.concat([add_df.PIID,del_df.PIID]))]

    changes_except_modnum_df = changes_df.drop_duplicates(subset=new_df.columns.drop(['url','modNumber','internal_id','usa_savings_url','version']),keep=False).sort_values(['PIID','version'])
    print("**Rows Modified - values other than 'modNumber' changed:",len(changes_except_modnum_df)/2)
    if(len(changes_except_modnum_df)>0):
        with pd.option_context('display.max_rows', None):
            print(changes_except_modnum_df.set_index(['PIID','version'])[['modNumber','business_name','claimed_savings','total_contract','description']])
    print()

    changes_only_modnum_df = pd.concat([changes_df,changes_except_modnum_df]).drop_duplicates(subset=new_df.columns.drop(['url','internal_id','usa_savings_url','version']),keep=False).sort_values(['PIID','version'])
    print("**Rows Modified - only 'modNumber' changed:",len(changes_except_modnum_df)/2)
    if(len(changes_only_modnum_df)>0):
        with pd.option_context('display.max_rows', None):
            print(changes_only_modnum_df.set_index(['PIID','version'])[['modNumber','business_name','description']])
    

def load_scrape(path):
    '''Load scrape at specified path to dataframe'''
    df = pd.read_csv(path)
    return df

def summarize_scrape(path):
    '''Print summary of a specific scrape (total rows, claimed savings, contract value, savings %)'''

    df = load_scrape(path)

    count_rows = len(df)
    sum_savings = df['claimed_savings'].sum()
    sum_ceiling = df['total_contract'].sum()

    print('****************')
    print('Summary of scrape at:',path)
    print(count_rows,'rows')
    print(f'claimed savings: {sum_savings:,.2f}')
    print(f'total ceiling: {sum_ceiling:,.2f}')
    print(f'claimed saving percent: {sum_savings/sum_ceiling*100:.3f}%')
    print()

def diff_latest(base_index=1):
    '''Apply diff on most recent scrape against reverse-chronological index of past scrapes
    Default index = 1, i.e. second most recent scrape'''

    scrapes = sorted(os.listdir('../data'),reverse=True)
    if base_index >= len(scrapes):
        print(f'Warning: requested index ({base_index}) is farther back than available scrapes. Using first available scrape instead ({len(scrapes-1)})')
        base_index=len(scrapes)-1

    path1 = os.path.abspath('../data/'+scrapes[0])
    path2 = os.path.abspath('../data/'+scrapes[base_index])

    summarize_scrape(path1)
    summarize_scrape(path2)

    diff_scrapes(path1,path2)

if __name__ == '__main__':
    diff_latest(-1)