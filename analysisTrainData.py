from dataclasses import replace
import pandas as pd
import numpy as np
import re
import os
import datetime

def readSchedule(target_schedule_path, start_station, end_station):
    
    """ ここにnew_formatか否かの判別を行うプログラムをかく """
    raw_datas = pd.read_excel(target_schedule_path,sheet_name=None,header=1) #新フォーマット
    len_sheet = 10 #(仮)
    new_format = 0 #新フォーマットか否か
    if len(raw_datas) > len_sheet: # シート数が多ければ旧フォーマット
        new_format = 1
        raw_datas = pd.read_excel(target_schedule_path,sheet_name=None,header=4)#　旧フォーマット header=4
    
    target_keys =  [key for key in list(raw_datas.keys()) if "Ｂ線・本線" in key]
    datas = pd.DataFrame(
            index=list(range(len(raw_datas[target_keys[0]]))),
            )
    for target_key in target_keys:
        #print(target_key)
        target_data = raw_datas[target_key].rename(
            columns={"列車番号":"駅名", "Unnamed: 1": "発着"}).copy()
        start_station_index = target_data[target_data["駅名"]==start_station].index[0]
        end_station_index = target_data[target_data["駅名"]==end_station].index[0] + 1
        info_index = target_data[target_data["駅名"]=="営業行先"].index[0]
        station_data_num = end_station_index - start_station_index
        if new_format == 0:
            """ 新フォーマット """
            target_data["駅名"][list(range(start_station_index+1, end_station_index+1, 3))] = target_data["駅名"][list(range(start_station_index, end_station_index, 3))].values.copy()
            """ 新フォーマット """
        else:# 旧フォーマット用↓
            target_data["駅名"][list(range(start_station_index+1, end_station_index+1, 2))] = target_data["駅名"][list(range(start_station_index, end_station_index, 2))].values.copy()

        #ーーーここまでは列車種別普通回送の行を消してない。
        target_data = target_data.T #扱いやすいように一度転置
        target_data = target_data[target_data.iloc[:,0]!="回送"] #列車種別回送を除外
        # ーー「 .1 」がついてるやつの.1を消す。
        target_data["index"] = target_data.index    #indexの文字列編集難しい ⇒ 一度indexを列に変更
        target_data["index"] = target_data["index"].str.strip(".1") #　.1を削除
        target_data.set_index('index',inplace=True) #indexを列からindexに戻す
        target_data = target_data.T#転置を戻す


        target_data = pd.concat([target_data[start_station_index:end_station_index+1], target_data[info_index:]]).reset_index(drop=True)

        start_index = target_data.loc[target_data["駅名"]=="他社列車種別"].index[0] + 1
        end_index = target_data.loc[target_data["駅名"]=="営業行先"].index[0]
        datas = pd.merge(datas,
                        target_data[start_index:end_index],
                        left_index=True, right_index=True, how="outer")
        datas = datas.rename(columns={"駅名_x":"駅名", "発着_x": "発着"})
        if "駅名_y" in datas.columns:
            datas = datas.drop(columns=["駅名_y", "発着_y"])
        datas.loc[:start_index-1, target_data.columns] = target_data[:start_index].to_numpy()
        datas = datas.reset_index(drop=True)
    datas = datas.astype("str").replace("\.",":",regex=True)
    for data_key in datas.columns:
        null_index = datas[data_key].isnull()
        valid_data = datas[data_key][~null_index]
        skip_station_index = valid_data.str.startswith("(")
        valid_data[skip_station_index] = np.nan
        datas[data_key][~null_index] = valid_data.copy()

    fix_columns = [data for data in list(datas.columns) if data.endswith('.1')]
    for fix_column in fix_columns:
        fix_position = datas[fix_column.replace(".1", "")].isnull()
        datas.loc[fix_position, fix_column.replace(".1", "")] = datas[fix_position][fix_column]
    datas = datas.drop(columns=fix_columns)
    datas = datas.loc[:datas[datas["駅名"]=="営業行先"].index[0]-1]
    if new_format == 0:
        """ 新フォーマット """
        # '---'を含む箇所でdatetimeにエラー発生　対処
        datas = dfmojierror(datas)
        """ 新フォーマット """
    ## 発着データに変えて、大手町順（東陽町出発順）に変更する。新フォーマットは西船橋順になっている。
    datas = datas_touyoutyoujun(datas, new_format)
    return datas