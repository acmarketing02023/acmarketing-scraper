import click
from database import init_db
from scraper import scrape_all_locations
from export import export_leads_to_csv


@click.group()
def cli():
    """ACMARKETING Lead Scraper CLI"""
    pass


@cli.command()
def init():
    """Initialize the database."""
    init_db()
    click.echo('✓ Database initialized')


@cli.command()
def scrape():
    """Run the scraper to pull fresh leads."""
    init_db()
    new_leads, updated_leads = scrape_all_locations()
    click.echo(f'\nSummary: {new_leads} new leads added, {updated_leads} updated')


@cli.command()
@click.option('--city', default=None, help='Filter by city')
@click.option('--category', default=None, help='Filter by category (concrete/hardscaping)')
@click.option('--no-website-only', is_flag=True, help='Only leads without websites')
@click.option('--priority-only', is_flag=True, help='Only leads with priority flags')
@click.option('--output', default=None, help='Output CSV path')
def export(city, category, no_website_only, priority_only, output):
    """Export leads to CSV."""
    filters = {}
    if city:
        filters['city'] = city
    if category:
        filters['category'] = category
    if no_website_only:
        filters['has_website'] = False
    if priority_only:
        filters['priority_only'] = True

    csv_path = export_leads_to_csv(filters=filters, output_path=output)
    click.echo(f'✓ Exported to {csv_path}')


if __name__ == '__main__':
    cli()
