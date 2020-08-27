# README

## price_basket.py
A shopping basket application that can calculate the total cost of all
items with any discounts from special offers, and print this in an
itemised bill.

## Installation
It is recommended you use a virtual environment:
```
cd <project_dir>
python3 -m venv venv
source venv/bin/activate
./setup.sh
```

### Usage
Run:
```
/path/to/price_basket.py ItemA ItemB ItemB
```

### Running tests
A test runner is not included; however 'pytest' should work out of the
box:
```
pip install pytest
cd <project_dir>
pytest
```

### Todo
- Unit tests for price_basket.py
- Unit tests for utils.py
- Integration test(s)
- Documentation around adding new products and special offers to the JSON
- Replace the JSON serialization with something better
  (e.g. Google Protobuf)
- If the JSON serialization is kept, it needs more validation and
  testing for badly formed data
- Internationalization (only GBP is supported at the moment)