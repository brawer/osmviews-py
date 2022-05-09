# osmviews

Python client for [OSMViews](https://osmviews.toolforge.org), a world-wide
ranking of geographic locations based on OpenStreetMap tile logs. Please
see the [main repository](https://github.com/brawer/osmviews) for background.


## Usage

```python
# pip install osmviews
import osmviews
with osmviews.OSMViews('path/to/osmviews.tiff') as o:
    print(f'Tokyo, Shibuya:      {o.rank( 35.658514, 139.701330):>9.2f}')
    print(f'Tokyo, Sumida:       {o.rank( 35.710719, 139.801547):>9.2f}')
    print(f'Zürich, Altstetten:  {o.rank( 47.391485,   8.488945):>9.2f}')
    print(f'Zürich, Witikon:     {o.rank( 47.358651,   8.590251):>9.2f}')
    print(f'Ushuaia, Costa Este: {o.rank(-54.794395, -68.251958):>9.2f}')
    print(f'Ushuaia, Las Reinas: {o.rank(-54.769225, -68.279174):>9.2f}')

Tokyo, Shibuya:      227437.98
Tokyo, Sumida:        60537.62
Zürich, Altstetten:   37883.31
Zürich, Witikon:      11711.94
Ushuaia, Costa Este:   2697.14
Ushuaia, Las Reinas:    257.89
```