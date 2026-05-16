"""
亚马逊SP广告分析工具包
Amazon SP Ads Analysis Toolkit

使用方法:
1. 将此文件放在与报表相同的目录
2. 修改 PRODUCT_PN 和 MARKET 变量
3. 运行: python3 analyze_ads.py
"""

import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# ========== 配置 ==========
PRODUCT_PN = 'SAPH101'  # 产品PN
MARKET = 'AE'           # 站点

# 报表文件名（根据实际情况修改）
FILE_SP_REPORT = '广告报告数据/SP广告报告 .xlsx'
FILE_SEARCH_TERMS = '广告报告数据/搜索词报告.xlsx'
FILE_SHOPPING_TIME = '广告报告数据/购物时间分析 .xlsx'
FILE_TRAFFIC = '广告报告数据/流量表现.xlsx'

# ========== 分析函数 ==========

def analyze_traffic():
    """分析流量表现报告"""
    print("\n" + "="*60)
    print("【流量表现分析】")
    print("="*60)
    
    try:
        df = pd.read_excel(FILE_TRAFFIC, sheet_name='Sheet1', header=0)
        df_p = df[(df['PN'] == PRODUCT_PN) & (df['Market-销售'] == MARKET)]
        
        total_sessions = df_p['Sessions - Total'].sum()
        total_units = df_p['Units Ordered'].sum()
        avg_cvr = df_p['Unit Session Percentage'].mean() * 100
        avg_buybox = df_p['Featured Offer (Buy Box) Percentage'].mean() * 100
        
        print(f"总Sessions: {total_sessions:,.0f}")
        print(f"总订单: {total_units:,.0f}")
        print(f"平均CVR: {avg_cvr:.2f}%")
        print(f"平均Buy Box: {avg_buybox:.1f}%")
        
        return total_sessions, total_units
    except Exception as e:
        print(f"错误: {e}")
        return 0, 0


def analyze_sp_performance():
    """分析SP广告效率"""
    print("\n" + "="*60)
    print("【SP广告效率分析】")
    print("="*60)
    
    try:
        df = pd.read_excel(FILE_SP_REPORT, 
                          sheet_name='SP投放商品（W）-更前两周', 
                          header=1)
        df_p = df[(df['PN'] == PRODUCT_PN) & (df['Market-销售'] == MARKET)]
        
        total_spend = df_p['Spend'].sum()
        total_sales = df_p['Sales'].sum()
        total_orders = df_p['Orders'].sum()
        total_clicks = df_p['Clicks'].sum()
        
        acos = total_spend / total_sales * 100 if total_sales > 0 else float('inf')
        roas = total_sales / total_spend if total_spend > 0 else 0
        cvr = total_orders / total_clicks * 100 if total_clicks > 0 else 0
        
        print(f"总花费: AED {total_spend:,.0f}")
        print(f"总销售: AED {total_sales:,.0f}")
        print(f"总订单: {total_orders:.0f}")
        print(f"ACOS: {acos:.1f}%")
        print(f"ROAS: {roas:.2f}")
        print(f"广告CVR: {cvr:.2f}%")
        
        return total_clicks, total_orders
    except Exception as e:
        print(f"错误: {e}")
        return 0, 0


def analyze_match_type():
    """分析匹配类型效率"""
    print("\n" + "="*60)
    print("【匹配类型效率】")
    print("="*60)
    
    try:
        df = pd.read_excel(FILE_SP_REPORT, 
                          sheet_name='SP无效花费（W）-更前两周', 
                          header=1)
        df_p = df[(df['PN'] == PRODUCT_PN) & (df['Market-销售角度'] == MARKET)]
        
        by_match = df_p.groupby('Match Type').agg({
            'Spend': 'sum',
            'Sales': 'sum',
            'Orders': 'sum'
        }).reset_index()
        
        by_match['ROAS'] = by_match['Sales'] / by_match['Spend']
        by_match['Spend%'] = by_match['Spend'] / by_match['Spend'].sum() * 100
        
        print(f"{'Match Type':<12} {'Spend%':>8} {'ROAS':>8}")
        print("-"*30)
        for _, row in by_match.sort_values('ROAS', ascending=False).iterrows():
            print(f"{row['Match Type']:<12} {row['Spend%']:>7.1f}% {row['ROAS']:>8.2f}")
    except Exception as e:
        print(f"错误: {e}")


def analyze_search_terms():
    """分析搜索词效率"""
    print("\n" + "="*60)
    print("【搜索词分析】")
    print("="*60)
    
    try:
        df = pd.read_excel(FILE_SEARCH_TERMS, 
                          sheet_name='广告搜索词（W）-更前两周', 
                          header=1)
        df_p = df[(df['PN'] == PRODUCT_PN) & (df['Market-销售'] == MARKET)]
        
        by_term = df_p.groupby('客户搜索词').agg({
            'Clicks': 'sum',
            'Spend': 'sum',
            'Sales': 'sum',
            'Orders': 'sum'
        }).reset_index()
        
        by_term['ROAS'] = by_term['Sales'] / by_term['Spend']
        by_term['ROAS'] = by_term['ROAS'].fillna(0)
        
        # 高效词
        high_eff = by_term[(by_term['ROAS'] >= 2.5) & (by_term['Orders'] >= 1)]
        high_eff = high_eff.sort_values('ROAS', ascending=False)
        
        print("\n--- 高效词 (ROAS >= 2.5) ---")
        print(f"{'Search Term':<30} {'Orders':>6} {'ROAS':>8}")
        for _, row in high_eff.head(10).iterrows():
            term = row['客户搜索词'][:28]
            print(f"{term:<30} {row['Orders']:>6.0f} {row['ROAS']:>8.2f}")
        
        # 否定候选
        neg = by_term[(by_term['Clicks'] >= 10) & (by_term['Orders'] == 0)]
        neg = neg.sort_values('Spend', ascending=False)
        
        print("\n--- 否定候选 (Clicks>=10, Orders=0) ---")
        print(f"{'Search Term':<30} {'Clicks':>6} {'Spend':>8}")
        for _, row in neg.head(10).iterrows():
            term = row['客户搜索词'][:28]
            print(f"{term:<30} {row['Clicks']:>6.0f} {row['Spend']:>8.0f}")
            
    except Exception as e:
        print(f"错误: {e}")


def analyze_hourly():
    """分析时段效率"""
    print("\n" + "="*60)
    print("【时段效率分析】")
    print("="*60)
    
    try:
        df = pd.read_excel(FILE_SHOPPING_TIME, 
                          sheet_name='SP广告活动By Hour-更前两周', 
                          header=1)
        df_p = df[(df['PN'] == PRODUCT_PN) & (df['Market-销售'] == MARKET)]
        
        # 提取小时
        df_p = df_p.copy()
        df_p['Hour'] = df_p['开始时间'].apply(lambda x: x.hour if hasattr(x, 'hour') else 0)
        
        by_hour = df_p.groupby('Hour').agg({
            '花费': 'sum',
            '7天总销售额': 'sum',
            '7天总订单数(#)': 'sum'
        }).reset_index()
        by_hour.rename(columns={'花费': 'Spend', '7天总销售额': 'Sales', '7天总订单数(#)': 'Orders'}, inplace=True)
        
        by_hour['ROAS'] = by_hour['Sales'] / by_hour['Spend']
        
        # 最佳时段
        best = by_hour.nlargest(5, 'ROAS')
        print("\n--- 最佳时段 (Top 5 ROAS) ---")
        print(f"{'Hour':>6} {'ROAS':>8} {'Orders':>8}")
        for _, row in best.iterrows():
            print(f"{int(row['Hour']):>6} {row['ROAS']:>8.2f} {row['Orders']:>8.0f}")
        
        # 最差时段
        worst = by_hour[by_hour['Spend'] > 0].nsmallest(5, 'ROAS')
        print("\n--- 最差时段 (Bottom 5 ROAS) ---")
        print(f"{'Hour':>6} {'ROAS':>8} {'Spend':>8}")
        for _, row in worst.iterrows():
            print(f"{int(row['Hour']):>6} {row['ROAS']:>8.2f} {row['Spend']:>8.0f}")
            
    except Exception as e:
        print(f"错误: {e}")


def main():
    """主分析流程"""
    print("="*60)
    print(f"亚马逊SP广告分析 - {PRODUCT_PN} ({MARKET})")
    print("="*60)
    
    # 1. 流量分析
    sessions, units = analyze_traffic()
    
    # 2. SP效率分析
    clicks, orders = analyze_sp_performance()
    
    # 3. 广告流量占比
    if sessions > 0 and clicks > 0:
        print(f"\n广告流量占比: {clicks/sessions*100:.1f}%")
        print(f"广告订单占比: {orders/units*100:.1f}%")
    
    # 4. 匹配类型分析
    analyze_match_type()
    
    # 5. 搜索词分析
    analyze_search_terms()
    
    # 6. 时段分析
    analyze_hourly()
    
    print("\n" + "="*60)
    print("分析完成！")
    print("="*60)


if __name__ == '__main__':
    main()
