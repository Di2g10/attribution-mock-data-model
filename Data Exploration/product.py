import src.connectors.snowflake


def main():
    deal_sql = "select * from KAINOS_DB.HUBSPOT_BLACKLINE_PROD.deal"
    deal_df = src.connectors.snowflake.query(deal_sql)
    print(deal_df.head(20).to_markdown())

    deal_sql = "select * from KAINOS_DB.DYNAMICS_365_PROD.product"
    deal_df = src.connectors.snowflake.query(deal_sql)
    print(deal_df.head(20).to_markdown())


if __name__ == "__main__":
    main()