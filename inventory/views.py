from django.shortcuts import get_object_or_404, render, redirect
from .models import Inventory
from django.contrib.auth.decorators import login_required
from .forms import AddInventoryForm,updateInventoryForm
from django.contrib import messages
import json
from django_pandas.io import read_frame
import plotly
import plotly.express as px

@login_required
def inventory_list(request):
    inventories = Inventory.objects.all()
    context = {
        "title": "Context Page",
        "inventories": inventories
    }
    return render(request, "inventory/inventory_list.html", context=context)


@login_required
def per_product_view(request, pk):
    inventory = get_object_or_404(Inventory, pk=pk)
    context = {
        "inventory": inventory
    }
    return render(request, "inventory/per_product.html", context=context)


@login_required
def add_product(request):
    if request.method == "POST":
        add_form = AddInventoryForm(request.POST)
        if add_form.is_valid():
            new_inventory = add_form.save(commit=False)

            # safe cleaned data access
            cost = add_form.cleaned_data['cost_per_item']
            qty = add_form.cleaned_data['quantity_sold']
            new_inventory.sales = float(cost) * float(qty)
            new_inventory.save()
            messages.success(request,'Sucessfully added product')
            return redirect("/inventory/")
    else:
        add_form = AddInventoryForm()

    return render(request, "inventory/inventory_add.html", {"form": add_form})

@login_required
def delete_inventory(request,pk):
    inventory=get_object_or_404(Inventory,pk=pk)
    inventory.delete()
    messages.success(request,'The product has been deleted')
    return redirect('/inventory/')


@login_required
def update_inventory(request,pk):
    inventory=get_object_or_404(Inventory,pk=pk)
    if request.method=='POST':
        updateForm=updateInventoryForm(data=request.POST)
        if updateForm.is_valid():
            inventory.name=updateForm.data['name']
            inventory.quantity_in_stock=updateForm.data['quantity_in_stock']
            inventory.quantity_sold=updateForm.data['quantity_sold']
            inventory.cost_per_item=updateForm.data['cost_per_item']
            inventory.sales=float(inventory.cost_per_item)*float(inventory.quantity_sold)
            inventory.save()
            messages.success(request,'The product has been Updated')
            return redirect('per_product_view', pk=pk)

    else:
        updateForm=updateInventoryForm(instance=inventory)
        context={'form':updateForm}
        return render(request,"inventory/inventory_update.html",context=context)



@login_required
def dashboard(request):
    inventories = Inventory.objects.all()
    df = read_frame(inventories)

    # ✅ 1. Sales over time
    sales_graph = df.groupby("last_sales_date", as_index=False)["sales"].sum()
    fig = px.line(sales_graph, x="last_sales_date", y="sales", title="Sales Over Time")

    # ✅ 2. Best performing products
    best_performing_product_df = (
        df.groupby("name", as_index=True)[["quantity_sold"]]  # only numeric column
        .sum()
        .sort_values(by="quantity_sold", ascending=False)
    )

    best_performing_product = px.bar(
        best_performing_product_df,
        x=best_performing_product_df.index,
        y="quantity_sold",
        title="Best Performing Product",
    )

    # ✅ 3. Most product in stock
    most_product_in_stock_df = (
        df.groupby("name", as_index=True)[["quantity_in_stock"]]  # only numeric column
        .sum()
        .sort_values(by="quantity_in_stock", ascending=False)
    )

    most_product_in_stock = px.pie(
        most_product_in_stock_df,
        names=most_product_in_stock_df.index,
        values="quantity_in_stock",
        title="Most Product in Stock",
    )

    # ✅ 4. Convert both graphs to JSON
    sales_graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    best_product_json = json.dumps(best_performing_product, cls=plotly.utils.PlotlyJSONEncoder)
    most_product_json = json.dumps(most_product_in_stock, cls=plotly.utils.PlotlyJSONEncoder)

    # ✅ 5. Send to template
    context = {
        "sales_graph": sales_graph_json,
        "best_performing_product": best_product_json,
        "most_product_in_stock": most_product_json,
    }

    return render(request, "inventory/dashboard.html", context)